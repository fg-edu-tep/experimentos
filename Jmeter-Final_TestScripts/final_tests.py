#!/usr/bin/env python3
"""
bite_load_test.py
─────────────────────────────────────────────────────────────────────────────
Torture test automatizado para Bite Latency Experiment.
Cubre los dos ASRs del sprint:

  ASR-ESCALABILIDAD  throughput ≥ 85 % baseline | P95 ≤ 5 000 ms | error ≤ 2 %
  ASR-LATENCIA       P95 ≤ 200 ms en GET /api/report/

Flujo de ejecución
──────────────────
  1. Genera el .jmx automáticamente (no necesitas tenerlo antes).
  2. Fase BASELINE  — carga baja para fijar métricas de referencia.
  3. Fase STRESS    — 12 000 usuarios concurrentes.
  4. En cada fase espera los 300 s de warmup del ASG y sondea el número
     de instancias activas cada 30 s.
  5. Parsea los .jtl: P50 / P95 / P99, throughput, error rate.
  6. Evalúa ambos ASRs y emite PASS / FAIL con el detalle.
  7. Genera gráficas (PNG) y exporta resumen CSV + Markdown.

Requisitos
──────────
  pip install boto3 matplotlib pandas
  Apache JMeter instalado localmente

Uso
───
  1. Edita la sección CONFIG.
  2. python bite_load_test.py
─────────────────────────────────────────────────────────────────────────────
"""

import subprocess, csv, os, sys, shutil, time, textwrap
from pathlib import Path
from datetime import datetime

# ── boto3 y matplotlib son opcionales (degradan con gracia si faltan) ────────
try:
    import boto3
    HAS_BOTO = False
except ImportError:
    HAS_BOTO = False
    print("[WARN] boto3 no instalado — el sondeo de instancias ASG se omitirá.")
    HAS_BOTO = False
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib no instalado — las gráficas se omitirán.")

try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False

# ═════════════════════════════════════════════════════════════════════════════
# CONFIG — edita esta sección antes de ejecutar
# ═════════════════════════════════════════════════════════════════════════════
JMETER_BIN  = r"H:\downloads\apache-jmeter-5.6.3\apache-jmeter-5.6.3\bin\jmeter.bat"   # Windows: jmeter.bat | Unix: jmeter.sh
RESULTS_DIR = r"C:\bite-results"

# Target
ALB_HOST    = "bite-alb-2069166410.us-east-1.elb.amazonaws.com"
ALB_PORT    = "80"
API_KEY     = "jmeter-load-test-key-67890"
PROJECT_ID  = "proj-001"
MONTH       = "2026-04"

# Cargas de prueba
BASELINE_THREADS = 200       # usuarios para fijar el baseline
STRESS_THREADS   = 12_000    # usuarios del torture test
RAMP_UP_S        = 120       # segundos para arrancar todos los threads
GAUSSIAN_DELAY   = 4_000     # ms — media del temporizador gaussiano
GAUSSIAN_STDDEV  = 2_000     # ms — desviación estándar

# ASR thresholds
ASR_THROUGHPUT_RATIO = 0.85   # stress throughput debe ser ≥ 85 % del baseline
ASR_P95_STRESS_MS    = 5_000  # P95 en stress ≤ 5 000 ms  (ASR escalabilidad)
ASR_P95_LATENCY_MS   = 200    # P95 en baseline ≤ 200 ms   (ASR latencia)
ASR_MAX_ERROR_PCT    = 2.0    # tasa de error ≤ 2 %

# ASG (solo si tienes boto3 y credenciales AWS configuradas)
ASG_NAME    = "bite-asg"
AWS_REGION  = "us-east-1"
ASG_WARMUP  = 300   # segundos — warmup configurado en el ASG
ASG_POLL_S  = 30    # segundos entre sondeos de instancias
# ═════════════════════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────────
# Generación del .jmx
# ─────────────────────────────────────────────────────────────────────────────
JMX_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan"
              testname="Bite Latency ASR Test" enabled="true">
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
    </TestPlan>
    <hashTree>

      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup"
                   testname="Users" enabled="true">
        <stringProp name="ThreadGroup.num_threads">{threads}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">{ramp_up}</stringProp>
        <boolProp name="ThreadGroup.same_user_on_next_iteration">false</boolProp>
        <elementProp name="ThreadGroup.main_controller"
                     elementType="LoopController"
                     guiclass="LoopControlPanel" testclass="LoopController">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <intProp  name="LoopController.loops">1</intProp>
        </elementProp>
      </ThreadGroup>
      <hashTree>

        <GaussianRandomTimer guiclass="GaussianRandomTimerGui"
                             testclass="GaussianRandomTimer"
                             testname="Think time 4s+-2s" enabled="true">
          <stringProp name="ConstantTimer.delay">{gaussian_delay}</stringProp>
          <stringProp name="RandomTimer.range">{gaussian_stddev}</stringProp>
        </GaussianRandomTimer>
        <hashTree/>

        <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager"
                       testname="Auth Header" enabled="true">
          <collectionProp name="HeaderManager.headers">
            <elementProp name="apikey" elementType="Header">
              <stringProp name="Header.name">apikey</stringProp>
              <stringProp name="Header.value">{api_key}</stringProp>
            </elementProp>
          </collectionProp>
        </HeaderManager>
        <hashTree/>

        <HTTPSamplerProxy guiclass="HttpTestSampleGui"
                          testclass="HTTPSamplerProxy"
                          testname="GET Report" enabled="true">
          <stringProp name="HTTPSampler.domain">{host}</stringProp>
          <stringProp name="HTTPSampler.port">{port}</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">/api/report/</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <boolProp   name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp   name="HTTPSampler.use_keepalive">true</boolProp>
          <stringProp name="HTTPSampler.connect_timeout">10000</stringProp>
          <stringProp name="HTTPSampler.response_timeout">30000</stringProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments"
                       guiclass="HTTPArgumentsPanel" testclass="Arguments">
            <collectionProp name="Arguments.arguments">
              <elementProp name="projectId" elementType="HTTPArgument">
                <boolProp   name="HTTPArgument.always_encode">false</boolProp>
                <stringProp name="Argument.name">projectId</stringProp>
                <stringProp name="Argument.value">{project_id}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
              </elementProp>
              <elementProp name="month" elementType="HTTPArgument">
                <boolProp   name="HTTPArgument.always_encode">false</boolProp>
                <stringProp name="Argument.name">month</stringProp>
                <stringProp name="Argument.value">{month}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
              </elementProp>
            </collectionProp>
          </elementProp>
        </HTTPSamplerProxy>
        <hashTree>
          <ResponseAssertion guiclass="AssertionGui"
                             testclass="ResponseAssertion"
                             testname="2xx OK" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="49586">200</stringProp>
            </collectionProp>
            <intProp name="Assertion.test_type">2</intProp>
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <boolProp name="Assertion.assume_success">false</boolProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>

      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""

def build_jmx(threads, ramp_up, out_path):
    content = JMX_TEMPLATE.format(
        threads        = threads,
        ramp_up        = ramp_up,
        gaussian_delay = GAUSSIAN_DELAY,
        gaussian_stddev= GAUSSIAN_STDDEV,
        host           = ALB_HOST,
        port           = ALB_PORT,
        api_key        = API_KEY,
        project_id     = PROJECT_ID,
        month          = MONTH,
    )
    Path(out_path).write_text(content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución de JMeter
# ─────────────────────────────────────────────────────────────────────────────
def run_jmeter(label, threads, ramp_up):
    """Lanza JMeter y devuelve la ruta al .jtl resultante."""
    run_dir = Path(RESULTS_DIR) / label
    run_dir.mkdir(parents=True, exist_ok=True)

    jmx  = str(run_dir / "test.jmx")
    jtl  = str(run_dir / "results.jtl")
    log  = str(run_dir / "jmeter.log")
    html = str(run_dir / "report")

    build_jmx(threads, ramp_up, jmx)

    if os.path.exists(html):
        shutil.rmtree(html)

    cmd = [
        JMETER_BIN, "-n",
        "-t", jmx,
        "-l", jtl,
        "-e", "-o", html,
        "-j", log,
    ]

    banner(f"Fase {label.upper()} — {threads:,} usuarios | ramp-up {ramp_up}s")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    if proc.returncode != 0:
        print(f"  [ERROR] JMeter salió con código {proc.returncode}")
        print(proc.stderr[-800:])
    else:
        print(f"  [OK] Completado en {elapsed/60:.1f} min → {jtl}")

    return jtl


# ─────────────────────────────────────────────────────────────────────────────
# Parseo del .jtl
# ─────────────────────────────────────────────────────────────────────────────
def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    idx = int(len(sorted_vals) * p / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]

def parse_jtl(jtl_path):
    """
    Parsea un .jtl de JMeter y devuelve un dict con:
      samples, avg_ms, p50, p95, p99, min_ms, max_ms,
      throughput_rps, error_pct, timestamps (lista), elapsed (lista)
    """
    elapsed_all = []
    errors      = 0
    timestamps  = []

    with open(jtl_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                elapsed_all.append(int(row["elapsed"]))
                timestamps.append(int(row["timeStamp"]))
                if row.get("success", "true").strip().lower() == "false":
                    errors += 1
            except (ValueError, KeyError):
                continue

    if not elapsed_all:
        return {}

    s = sorted(elapsed_all)
    total   = len(s)
    avg     = sum(s) / total
    dur_s   = (max(timestamps) - min(timestamps)) / 1000.0 if len(timestamps) > 1 else 1
    tput    = total / dur_s if dur_s > 0 else total

    return {
        "samples":       total,
        "avg_ms":        round(avg, 1),
        "p50":           percentile(s, 50),
        "p95":           percentile(s, 95),
        "p99":           percentile(s, 99),
        "min_ms":        s[0],
        "max_ms":        s[-1],
        "throughput_rps":round(tput, 2),
        "error_pct":     round(errors / total * 100, 2),
        "timestamps":    timestamps,
        "elapsed":       elapsed_all,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sondeo ASG
# ─────────────────────────────────────────────────────────────────────────────
def poll_asg_instances():
    """Devuelve el número de instancias InService en el ASG."""
    if not HAS_BOTO:
        return None
    try:
        client = boto3.client("autoscaling", region_name=AWS_REGION)
        resp   = client.describe_auto_scaling_groups(
                     AutoScalingGroupNames=[ASG_NAME])
        group  = resp["AutoScalingGroups"][0]
        return sum(1 for i in group["Instances"]
                   if i["LifecycleState"] == "InService")
    except Exception as e:
        print(f"  [WARN] No se pudo leer el ASG: {e}")
        return None

def monitor_asg_during_warmup(phase_label, total_wait_s):
    timeline = []
    t0 = time.time()
    print(f"\n  Esperando {total_wait_s}s ({phase_label}). Log de timestamps cada {ASG_POLL_S}s…")
    while time.time() - t0 < total_wait_s:
        elapsed = int(time.time() - t0)
        ts_human = datetime.now().strftime("%H:%M:%S")
        timeline.append((elapsed, ts_human))
        print(f"    t+{elapsed:>4}s  [{ts_human}]  — revisar email SNS para instancias")
        time.sleep(ASG_POLL_S)
    return timeline


# ─────────────────────────────────────────────────────────────────────────────
# Gráficas
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {"baseline": "#4C72B0", "stress": "#DD8452"}

def _save(fig, name):
    path = Path(RESULTS_DIR) / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Gráfica: {path}")

def plot_latency_comparison(m_base, m_stress):
    if not HAS_MPL:
        return
    labels = ["P50", "P95", "P99", "Avg"]
    b_vals = [m_base["p50"],   m_base["p95"],   m_base["p99"],   m_base["avg_ms"]]
    s_vals = [m_stress["p50"], m_stress["p95"], m_stress["p99"], m_stress["avg_ms"]]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    w = 0.35
    ax.bar([i - w/2 for i in x], b_vals, w, label=f"Baseline ({BASELINE_THREADS} users)",
           color=COLORS["baseline"])
    ax.bar([i + w/2 for i in x], s_vals, w, label=f"Stress ({STRESS_THREADS:,} users)",
           color=COLORS["stress"])

    # Líneas de umbral
    ax.axhline(ASR_P95_LATENCY_MS, color="red",    linestyle="--", lw=1.2,
               label=f"ASR latencia P95 ≤ {ASR_P95_LATENCY_MS} ms")
    ax.axhline(ASR_P95_STRESS_MS,  color="orange", linestyle="--", lw=1.2,
               label=f"ASR escalabilidad P95 ≤ {ASR_P95_STRESS_MS} ms")

    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylabel("Latencia (ms)")
    ax.set_title("Comparación de latencia — Baseline vs Stress")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "latencia_comparacion.png")

def plot_throughput(m_base, m_stress):
    if not HAS_MPL:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    vals   = [m_base["throughput_rps"], m_stress["throughput_rps"]]
    labels = [f"Baseline\n({BASELINE_THREADS} users)", f"Stress\n({STRESS_THREADS:,} users)"]
    bars   = ax.bar(labels, vals, color=[COLORS["baseline"], COLORS["stress"]], width=0.4)

    # Línea 85 % del baseline
    thr_85 = m_base["throughput_rps"] * ASR_THROUGHPUT_RATIO
    ax.axhline(thr_85, color="red", linestyle="--", lw=1.2,
               label=f"85 % baseline = {thr_85:.1f} req/s")

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val:.1f}", ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("Throughput (req/s)")
    ax.set_title("Throughput — Baseline vs Stress")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "throughput.png")

def plot_error_rate(m_base, m_stress):
    if not HAS_MPL:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    vals   = [m_base["error_pct"], m_stress["error_pct"]]
    labels = [f"Baseline\n({BASELINE_THREADS} users)", f"Stress\n({STRESS_THREADS:,} users)"]
    bars   = ax.bar(labels, vals, color=[COLORS["baseline"], COLORS["stress"]], width=0.4)

    ax.axhline(ASR_MAX_ERROR_PCT, color="red", linestyle="--", lw=1.2,
               label=f"Umbral ≤ {ASR_MAX_ERROR_PCT} %")

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{val:.2f} %", ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("Tasa de error (%)")
    ax.set_title("Tasa de error — Baseline vs Stress")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "error_rate.png")

def plot_asg_timeline(timeline):
    if not HAS_MPL or not timeline:
        return
    ts, counts = zip(*timeline)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.step(ts, counts, where="post", color=COLORS["stress"], lw=2)
    ax.fill_between(ts, counts, step="post", alpha=0.15, color=COLORS["stress"])
    ax.axvline(ASG_WARMUP, color="gray", linestyle="--", lw=1,
               label=f"Warmup {ASG_WARMUP}s")
    ax.set_xlabel("Tiempo desde inicio de fase stress (s)")
    ax.set_ylabel("Instancias InService")
    ax.set_title("Elasticidad del ASG durante la prueba de stress")
    ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, "asg_elasticidad.png")

def plot_latency_distribution(m_base, m_stress):
    """Histograma superpuesto de tiempos de respuesta."""
    if not HAS_MPL:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    cap = 10_000   # recortar outliers para legibilidad
    b_data = [v for v in m_base.get("elapsed", [])   if v <= cap]
    s_data = [v for v in m_stress.get("elapsed", []) if v <= cap]
    ax.hist(b_data, bins=60, alpha=0.6, color=COLORS["baseline"],
            label=f"Baseline ({BASELINE_THREADS} users)", density=True)
    ax.hist(s_data, bins=60, alpha=0.6, color=COLORS["stress"],
            label=f"Stress ({STRESS_THREADS:,} users)", density=True)
    ax.axvline(ASR_P95_LATENCY_MS, color="red",    linestyle="--", lw=1.2,
               label=f"ASR latencia {ASR_P95_LATENCY_MS} ms")
    ax.axvline(ASR_P95_STRESS_MS,  color="orange", linestyle="--", lw=1.2,
               label=f"ASR escalabilidad {ASR_P95_STRESS_MS} ms")
    ax.set_xlabel("Tiempo de respuesta (ms)")
    ax.set_ylabel("Densidad")
    ax.set_title("Distribución de latencias (recortado a 10 000 ms)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    _save(fig, "distribucion_latencias.png")


# ─────────────────────────────────────────────────────────────────────────────
# Evaluación de ASRs
# ─────────────────────────────────────────────────────────────────────────────
def check_asr(m_base, m_stress):
    results = {}

    # ASR-LATENCIA: P95 baseline ≤ 200 ms
    results["asr_latencia_p95"] = {
        "desc":    "P95 latencia baseline ≤ 200 ms",
        "valor":   m_base["p95"],
        "umbral":  ASR_P95_LATENCY_MS,
        "pass":    m_base["p95"] <= ASR_P95_LATENCY_MS,
    }

    # ASR-ESCALABILIDAD: throughput stress ≥ 85 % del baseline
    thr_85 = m_base["throughput_rps"] * ASR_THROUGHPUT_RATIO
    results["asr_throughput"] = {
        "desc":    f"Throughput stress ≥ 85 % baseline ({thr_85:.1f} req/s)",
        "valor":   m_stress["throughput_rps"],
        "umbral":  thr_85,
        "pass":    m_stress["throughput_rps"] >= thr_85,
    }

    # ASR-ESCALABILIDAD: P95 stress ≤ 5 000 ms
    results["asr_p95_stress"] = {
        "desc":    "P95 latencia stress ≤ 5 000 ms",
        "valor":   m_stress["p95"],
        "umbral":  ASR_P95_STRESS_MS,
        "pass":    m_stress["p95"] <= ASR_P95_STRESS_MS,
    }

    # ASR-ESCALABILIDAD: error stress ≤ 2 %
    results["asr_error"] = {
        "desc":    "Tasa de error stress ≤ 2 %",
        "valor":   m_stress["error_pct"],
        "umbral":  ASR_MAX_ERROR_PCT,
        "pass":    m_stress["error_pct"] <= ASR_MAX_ERROR_PCT,
    }

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Exportación
# ─────────────────────────────────────────────────────────────────────────────
def save_csv(m_base, m_stress):
    out = Path(RESULTS_DIR) / "resumen_asr.csv"
    fields = ["fase", "threads", "samples", "avg_ms", "p50", "p95", "p99",
              "min_ms", "max_ms", "throughput_rps", "error_pct"]
    rows = [
        {"fase": "baseline", "threads": BASELINE_THREADS, **{k: m_base.get(k)   for k in fields[2:]}},
        {"fase": "stress",   "threads": STRESS_THREADS,   **{k: m_stress.get(k) for k in fields[2:]}},
    ]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"  → CSV: {out}")

def save_markdown(m_base, m_stress, asr_results, asg_timeline):
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    out  = Path(RESULTS_DIR) / "informe_asr.md"

    def status(passed): return "✅ PASS" if passed else "❌ FAIL"

    lines = [
        f"# Informe de pruebas de carga — Bite Latency Experiment",
        f"",
        f"**Fecha:** {now}  ",
        f"**ALB:** `{ALB_HOST}`  ",
        f"**Endpoint:** `GET /api/report/?projectId={PROJECT_ID}&month={MONTH}`  ",
        f"**Timer:** GaussianRandomTimer {GAUSSIAN_DELAY}ms ± {GAUSSIAN_STDDEV}ms",
        f"",
        f"---",
        f"",
        f"## Resultados por fase",
        f"",
        f"| Métrica | Baseline ({BASELINE_THREADS} users) | Stress ({STRESS_THREADS:,} users) |",
        f"|---|---|---|",
        f"| Muestras        | {m_base['samples']:,}       | {m_stress['samples']:,}       |",
        f"| Avg (ms)        | {m_base['avg_ms']}          | {m_stress['avg_ms']}          |",
        f"| P50 (ms)        | {m_base['p50']}             | {m_stress['p50']}             |",
        f"| P95 (ms)        | {m_base['p95']}             | {m_stress['p95']}             |",
        f"| P99 (ms)        | {m_base['p99']}             | {m_stress['p99']}             |",
        f"| Min (ms)        | {m_base['min_ms']}          | {m_stress['min_ms']}          |",
        f"| Max (ms)        | {m_base['max_ms']}          | {m_stress['max_ms']}          |",
        f"| Throughput (r/s)| {m_base['throughput_rps']}  | {m_stress['throughput_rps']}  |",
        f"| Error (%)       | {m_base['error_pct']}       | {m_stress['error_pct']}       |",
        f"",
        f"---",
        f"",
        f"## Evaluación de ASRs",
        f"",
        f"| ASR | Descripción | Valor medido | Umbral | Resultado |",
        f"|---|---|---|---|---|",
    ]

    for key, r in asr_results.items():
        lines.append(
            f"| {key} | {r['desc']} | {r['valor']} | {r['umbral']} | {status(r['pass'])} |"
        )

    all_pass = all(r["pass"] for r in asr_results.values())
    lines += [
        f"",
        f"**Veredicto general: {status(all_pass)}**",
        f"",
        f"---",
        f"",
        f"## Elasticidad del ASG",
        f"",
    ]

    if asg_timeline:
        lines += [
            f"| t relativo (s) | Timestamp local | Evento sugerido |",
            f"|---|---|---|",
        ]
        for ts, ts_human in asg_timeline:
            lines.append(f"| {ts} | {ts_human} | _(cruzar con email SNS)_ |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Configuración de la prueba",
        f"",
        f"```",
        f"Baseline threads : {BASELINE_THREADS}",
        f"Stress threads   : {STRESS_THREADS:,}",
        f"Ramp-up          : {RAMP_UP_S}s",
        f"Gaussian timer   : {GAUSSIAN_DELAY}ms ± {GAUSSIAN_STDDEV}ms",
        f"ASG warmup       : {ASG_WARMUP}s",
        f"```",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → Markdown: {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def banner(msg):
    print(f"\n{'═'*60}")
    print(f"  {msg}")
    print(f"{'═'*60}")

def check_prereqs():
    errors = []
    if not os.path.exists(JMETER_BIN):
        errors.append(f"JMeter no encontrado: {JMETER_BIN}")
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    check_prereqs()
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

    # ── FASE BASELINE ────────────────────────────────────────────────────────
    jtl_base = run_jmeter("baseline", BASELINE_THREADS, ramp_up=30)
    if not os.path.exists(jtl_base):
        sys.exit("[ERROR] No se generó el .jtl del baseline.")
    m_base = parse_jtl(jtl_base)
    if not m_base:
        sys.exit("[ERROR] El .jtl del baseline está vacío.")

    banner("BASELINE completado")
    print(f"  Samples   : {m_base['samples']:,}")
    print(f"  Avg       : {m_base['avg_ms']} ms")
    print(f"  P50/P95/P99: {m_base['p50']} / {m_base['p95']} / {m_base['p99']} ms")
    print(f"  Throughput: {m_base['throughput_rps']} req/s")
    print(f"  Error     : {m_base['error_pct']} %")

    # ── ESPERAR WARMUP ASG antes del stress ──────────────────────────────────
    asg_timeline = []
    if HAS_BOTO:
        banner(f"Warmup ASG ({ASG_WARMUP}s) — monitorizando instancias")
        asg_timeline = monitor_asg_during_warmup("pre-stress", ASG_WARMUP)

    # ── FASE STRESS ──────────────────────────────────────────────────────────
    jtl_stress = run_jmeter("stress", STRESS_THREADS, ramp_up=RAMP_UP_S)
    if not os.path.exists(jtl_stress):
        sys.exit("[ERROR] No se generó el .jtl del stress.")
    m_stress = parse_jtl(jtl_stress)
    if not m_stress:
        sys.exit("[ERROR] El .jtl del stress está vacío.")

    # Seguir monitorizando el ASG durante el stress (los primeros ASG_WARMUP s)
    if HAS_BOTO:
        banner("Monitorizando ASG durante el stress")
        asg_timeline += monitor_asg_during_warmup("during-stress", ASG_WARMUP)

    banner("STRESS completado")
    print(f"  Samples   : {m_stress['samples']:,}")
    print(f"  Avg       : {m_stress['avg_ms']} ms")
    print(f"  P50/P95/P99: {m_stress['p50']} / {m_stress['p95']} / {m_stress['p99']} ms")
    print(f"  Throughput: {m_stress['throughput_rps']} req/s")
    print(f"  Error     : {m_stress['error_pct']} %")

    # ── EVALUACIÓN ASRs ──────────────────────────────────────────────────────
    asr = check_asr(m_base, m_stress)

    banner("EVALUACIÓN DE ASRs")
    all_pass = True
    for key, r in asr.items():
        icon = "✅" if r["pass"] else "❌"
        print(f"  {icon} {r['desc']}")
        print(f"       Medido: {r['valor']}  |  Umbral: {r['umbral']}")
        all_pass = all_pass and r["pass"]
    print(f"\n  Veredicto: {'✅ TODOS LOS ASRs PASAN' if all_pass else '❌ ALGÚN ASR FALLÓ'}")

    # ── SALIDAS ──────────────────────────────────────────────────────────────
    banner("Generando salidas")
    save_csv(m_base, m_stress)
    save_markdown(m_base, m_stress, asr, asg_timeline)
    plot_latency_comparison(m_base, m_stress)
    plot_throughput(m_base, m_stress)
    plot_error_rate(m_base, m_stress)
    plot_latency_distribution(m_base, m_stress)
    if asg_timeline:
        plot_asg_timeline(asg_timeline)

    banner("DONE")
    print(f"  Resultados en: {RESULTS_DIR}")
    print(textwrap.dedent(f"""
      Archivos generados:
        baseline/results.jtl         — raw JMeter baseline
        baseline/report/index.html   — dashboard HTML baseline
        stress/results.jtl           — raw JMeter stress
        stress/report/index.html     — dashboard HTML stress
        resumen_asr.csv              — tabla comparativa
        informe_asr.md               — informe Markdown con ASRs
        latencia_comparacion.png     — gráfica P50/P95/P99
        throughput.png               — gráfica throughput
        error_rate.png               — gráfica tasa de error
        distribucion_latencias.png   — histograma de latencias
        asg_elasticidad.png          — timeline instancias ASG (si boto3)
    """))


if __name__ == "__main__":
    main()