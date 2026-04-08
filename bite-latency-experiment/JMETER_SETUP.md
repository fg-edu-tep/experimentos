# JMeter Load Testing Setup Guide

Complete guide to set up Apache JMeter for load testing the Bite Latency Experiment API with Kong Gateway.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Database Population](#database-population)
- [JMeter Installation](#jmeter-installation)
- [Test Plan Configuration](#test-plan-configuration)
- [Running Load Tests](#running-load-tests)
- [Analyzing Results](#analyzing-results)

---

## Prerequisites

### 1. Populated Database

First, populate your database with test data:

#### On AWS Server:
```bash
# SSH into AWS
ssh ubuntu@ec2-13-222-13-14.compute-1.amazonaws.com

# Navigate to project
cd ~/experimentos/bite-latency-experiment

# Populate database with 100 projects, 12 months each
docker compose exec django-app python populate_test_data.py --projects 100 --months 12 --warm-cache

# Verify data
docker compose exec django-app python manage.py shell -c "
from reports.models import Report
print(f'Total reports in database: {Report.objects.count()}')
"
```

#### Locally (for development):
```bash
cd bite-latency-experiment

# Activate virtual environment if using one
# source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Run population script
python populate_test_data.py --projects 50 --months 6 --warm-cache
```

### 2. API Endpoint

Make sure your API is accessible:
- **Production**: `http://ec2-13-222-13-14.compute-1.amazonaws.com:8000`
- **Local**: `http://localhost:8000`

### 3. API Key

Use the JMeter-specific API key:
```
jmeter-load-test-key-67890
```

---

## JMeter Installation

### Windows:
1. Download from https://jmeter.apache.org/download_jmeter.cgi
2. Extract to `C:\jmeter`
3. Add to PATH or run from `C:\jmeter\bin\jmeter.bat`

### Linux/Mac:
```bash
# Download
wget https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.6.3.tgz

# Extract
tar -xzf apache-jmeter-5.6.3.tgz

# Run
cd apache-jmeter-5.6.3/bin
./jmeter
```

### Using Package Managers:
```bash
# macOS
brew install jmeter

# Ubuntu/Debian
sudo apt install jmeter

# Arch Linux
sudo pacman -S jmeter
```

---

## Test Plan Configuration

### Option 1: Use Existing Test Plan (Recommended)

If you have existing JMeter test plans in the repository:

```bash
# Check for existing test plans
ls jmeter/*.jmx

# Open in JMeter GUI
jmeter -t jmeter/load_test.jmx
```

### Option 2: Create New Test Plan from Scratch

#### Step 1: Create Test Plan

1. Open JMeter
2. Right-click **Test Plan** → Add → Threads (Users) → **Thread Group**

#### Step 2: Configure Thread Group

**Thread Group Settings:**
- **Number of Threads (users)**: 50
- **Ramp-up period (seconds)**: 10
- **Loop Count**: 100

This simulates:
- 50 concurrent users
- Ramping up over 10 seconds
- Each user makes 100 requests
- **Total requests**: 5,000

#### Step 3: Add HTTP Request Defaults

1. Right-click **Thread Group** → Add → Config Element → **HTTP Request Defaults**
2. Configure:
   - **Server Name**: `ec2-13-222-13-14.compute-1.amazonaws.com`
   - **Port Number**: `8000`
   - **Protocol**: `http`

#### Step 4: Add HTTP Header Manager

1. Right-click **Thread Group** → Add → Config Element → **HTTP Header Manager**
2. Add header:
   - **Name**: `apikey`
   - **Value**: `jmeter-load-test-key-67890`

#### Step 5: Add CSV Data Set Config (for varied requests)

1. Right-click **Thread Group** → Add → Config Element → **CSV Data Set Config**
2. Create a file `test_data.csv`:

```csv
projectId,month
proj-001,2026-04
proj-002,2026-03
proj-003,2026-02
proj-004,2026-01
proj-005,2025-12
proj-006,2025-11
proj-007,2025-10
proj-008,2025-09
proj-009,2025-08
proj-010,2025-07
```

3. Configure CSV Data Set:
   - **Filename**: `test_data.csv`
   - **Variable Names**: `projectId,month`
   - **Recycle on EOF**: True
   - **Stop thread on EOF**: False

#### Step 6: Add HTTP Request Sampler

1. Right-click **Thread Group** → Add → Sampler → **HTTP Request**
2. Configure:
   - **Name**: `Get Report API`
   - **Method**: `GET`
   - **Path**: `/api/report/`
   - **Parameters**:
     - `projectId`: `${projectId}`
     - `month`: `${month}`

#### Step 7: Add Listeners (for results)

Add these listeners to monitor performance:

1. **View Results Tree** (for debugging)
   - Right-click **Thread Group** → Add → Listener → **View Results Tree**

2. **Summary Report**
   - Right-click **Thread Group** → Add → Listener → **Summary Report**

3. **Aggregate Report**
   - Right-click **Thread Group** → Add → Listener → **Aggregate Report**

4. **Response Time Graph**
   - Right-click **Thread Group** → Add → Listener → **Response Time Graph**

5. **Active Threads Over Time**
   - Right-click **Thread Group** → Add → Listener → **Active Threads Over Time**

#### Step 8: Add Assertions (optional)

1. Right-click **HTTP Request** → Add → Assertions → **Response Assertion**
2. Configure:
   - **Apply to**: Main sample only
   - **Response Field**: Response Code
   - **Pattern Matching Rules**: Equals
   - **Patterns to Test**: `200`

#### Step 9: Save Test Plan

File → Save Test Plan As → `load_test_report_api.jmx`

---

## Running Load Tests

### GUI Mode (Development/Testing)

1. Open JMeter
2. Load test plan: `File → Open → load_test_report_api.jmx`
3. Click the green **Start** button (▶)
4. Monitor results in real-time

**Note**: GUI mode is resource-intensive. Use for test development only.

### CLI Mode (Production/Realistic Testing)

For accurate performance testing, always use CLI mode:

```bash
# Basic run
jmeter -n -t load_test_report_api.jmx -l results.jtl

# With HTML report
jmeter -n -t load_test_report_api.jmx -l results.jtl -e -o report/

# With custom properties
jmeter -n -t load_test_report_api.jmx \
  -l results.jtl \
  -e -o report/ \
  -Jusers=100 \
  -Jrampup=20 \
  -Jloops=50
```

**Parameters:**
- `-n`: Non-GUI mode
- `-t`: Test plan file
- `-l`: Log file for results
- `-e`: Generate report at end
- `-o`: Output folder for HTML report
- `-J`: Set JMeter properties

### Remote Testing (AWS Server)

If JMeter is installed on AWS:

```bash
ssh ubuntu@ec2-13-222-13-14.compute-1.amazonaws.com

# Install JMeter
sudo apt update
sudo apt install -y openjdk-11-jdk wget
wget https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.6.3.tgz
tar -xzf apache-jmeter-5.6.3.tgz

# Run test
cd apache-jmeter-5.6.3/bin
./jmeter -n -t ~/experimentos/bite-latency-experiment/jmeter/load_test.jmx \
  -l results.jtl -e -o ~/jmeter-report/
```

---

## Test Scenarios

### Scenario 1: Baseline Performance Test
**Goal**: Measure normal operation performance

```
Users: 10
Ramp-up: 5 seconds
Duration: 60 seconds
```

### Scenario 2: Stress Test
**Goal**: Find breaking point

```
Users: 100
Ramp-up: 30 seconds
Duration: 300 seconds (5 minutes)
```

### Scenario 3: Spike Test
**Goal**: Test sudden traffic surge

```
Users: 200
Ramp-up: 5 seconds (sudden spike)
Duration: 60 seconds
```

### Scenario 4: Endurance Test
**Goal**: Test long-term stability

```
Users: 50
Ramp-up: 10 seconds
Duration: 3600 seconds (1 hour)
```

### Scenario 5: Rate Limit Test
**Goal**: Verify Kong rate limiting (100/min, 1000/hour)

```
Users: 20
Ramp-up: 0 seconds (immediate)
Loops: 200 (4000 total requests)
```

Expected: After 100 requests/minute, should see 429 errors.

---

## Quick Start Commands

### 1. Populate Database
```bash
# On AWS
ssh ubuntu@ec2-13-222-13-14.compute-1.amazonaws.com
cd ~/experimentos/bite-latency-experiment
docker compose exec django-app python populate_test_data.py --projects 100 --months 12 --warm-cache
```

### 2. Verify API
```bash
curl -H "apikey: jmeter-load-test-key-67890" \
  "http://ec2-13-222-13-14.compute-1.amazonaws.com:8000/api/report/?projectId=proj-001&month=2026-04"
```

### 3. Run JMeter Test
```bash
# Download test plan (if in repo)
# Or use the one you created

jmeter -n -t load_test_report_api.jmx -l results.jtl -e -o report/
```

### 4. View Results
```bash
# Open HTML report
cd report/
python -m http.server 8888

# Navigate to: http://localhost:8888
```

---

## Analyzing Results

### Key Metrics to Monitor

1. **Throughput**: Requests per second
   - Target: >100 req/s

2. **Response Time**:
   - Average: <200ms
   - 90th Percentile: <500ms
   - 95th Percentile: <1000ms
   - Max: <2000ms

3. **Error Rate**: <1%

4. **Rate Limiting**:
   - Should see 429 errors after exceeding limits
   - 100 requests/minute per API key
   - 1000 requests/hour per API key

### HTML Report Sections

1. **Dashboard**: Overview of key metrics
2. **Statistics**: Detailed statistics per request
3. **Error Table**: All errors encountered
4. **Response Times Over Time**: Performance timeline
5. **Throughput Over Time**: Request rate timeline

### Common Issues

#### High Response Times
- **Cause**: Database not indexed properly
- **Solution**: Check database queries, add indexes

#### 429 Errors
- **Cause**: Rate limiting triggered
- **Solution**: Expected behavior, reduce request rate or increase limits

#### 500 Errors
- **Cause**: Server errors
- **Solution**: Check Django logs: `docker compose logs django-app`

#### 400 Errors
- **Cause**: Invalid request parameters
- **Solution**: Check test data CSV file

---

## Sample Test Data Generator

Create `generate_test_data.py`:

```python
import csv
from datetime import datetime, timedelta

# Generate 100 project/month combinations
with open('test_data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['projectId', 'month'])

    base_date = datetime.now()
    for i in range(1, 101):
        project_id = f"proj-{i:03d}"
        # Random month within last 12 months
        month_offset = i % 12
        month_date = base_date - timedelta(days=30 * month_offset)
        month_str = month_date.strftime('%Y-%m')

        writer.writerow([project_id, month_str])

print("Generated test_data.csv with 100 combinations")
```

Run: `python generate_test_data.py`

---

## Monitoring During Load Tests

### Check Kong Metrics
```bash
curl http://ec2-13-222-13-14.compute-1.amazonaws.com:8001/status
```

### Check Django Performance
```bash
# On AWS
docker compose logs -f django-app

# Check container stats
docker stats bite-django
```

### Check Rate Limiting
```bash
# Make requests and watch headers
curl -v -H "apikey: jmeter-load-test-key-67890" \
  "http://ec2-13-222-13-14.compute-1.amazonaws.com:8000/api/health/" \
  2>&1 | grep -i ratelimit
```

---

## Best Practices

1. **Always warm up** the cache before testing
2. **Use CLI mode** for realistic tests
3. **Run from external machine** for network realism
4. **Monitor server resources** during tests
5. **Start with low load** and gradually increase
6. **Test one scenario at a time**
7. **Document results** for comparison
8. **Clean up test data** after tests

---

## Troubleshooting

### JMeter Issues

**Problem**: Out of memory errors
```bash
# Increase heap size
export HEAP="-Xms1g -Xmx4g"
jmeter -n -t test.jmx -l results.jtl
```

**Problem**: Can't connect to server
- Check firewall/security groups
- Verify API is running: `curl http://server:8000/api/health/`
- Check network from JMeter machine

### API Issues

**Problem**: All requests failing
```bash
# Check if API is up
curl http://ec2-13-222-13-14.compute-1.amazonaws.com:8000/api/health/

# Check Kong
curl http://ec2-13-222-13-14.compute-1.amazonaws.com:8001/status

# Check Django logs
docker compose logs django-app
```

---

## Next Steps

1. ✅ Populate database with test data
2. ✅ Install JMeter
3. ✅ Create/load test plan
4. ✅ Run baseline test
5. ✅ Analyze results
6. ✅ Optimize based on findings
7. ✅ Repeat with increased load

---

## Resources

- **JMeter Documentation**: https://jmeter.apache.org/usermanual/
- **Kong Rate Limiting**: https://docs.konghq.com/hub/kong-inc/rate-limiting/
- **Django Performance**: https://docs.djangoproject.com/en/stable/topics/performance/
- **AWS CloudWatch**: For monitoring server metrics

---

**Good luck with your load testing!** 🚀
