import psycopg2
from psycopg2 import OperationalError

def test_connection():
    # Configuración de la conexión
    config = {
        "host": "ec2-54-83-92-122.compute-1.amazonaws.com",
        "port": 5434,
        "database": "bite_latency", # Cambia por el nombre de tu DB (ej. 'kong')
        "user": "bite_user",     # Tu usuario
        "password": "bite_pass" # Tu contraseña
    }

    print(f"Intentando conectar a {config['host']} en el puerto {config['port']}...")

    try:
        # Intento de conexión
        connection = psycopg2.connect(**config)
        
        # Crear un cursor para ejecutar una consulta simple
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        print("✅ ¡Conexión exitosa!")
        print(f"Versión de la base de datos: {db_version[0]}")

        # Cerrar conexión
        cursor.close()
        connection.close()

    except OperationalError as e:
        print("❌ Error al conectar a la base de datos:")
        print(f"Detalle: {e}")

if __name__ == "__main__":
    test_connection()