import mysql.connector
import os
from datetime import datetime

def dump_database_via_connection(host, user, password, database):
    # Cria a pasta 'dumpsDB' se não existir
    dump_dir = "dumpsDB"
    os.makedirs(dump_dir, exist_ok=True)
    
    # Define o nome do arquivo de dump com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = os.path.join(dump_dir, f"{database}_dump_{timestamp}.sql")
    
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        with open(dump_file, 'w') as f:
            for result in cursor.execute(f"SHOW TABLES", multi=True):
                if result.with_rows:
                    for row in result.fetchall():
                        table = row[0]
                        cursor.execute(f"SHOW CREATE TABLE `{table}`")
                        create_table_stmt = cursor.fetchone()[1]
                        f.write(f"{create_table_stmt};\n")
                        cursor.execute(f"SELECT * FROM `{table}`")
                        rows = cursor.fetchall()
                        for row in rows:
                            values = ', '.join([f"'{str(item).replace('\'', '\\\'')}'" if item is not None else 'NULL' for item in row])
                            f.write(f"INSERT INTO `{table}` VALUES ({values});\n")
        print(f"Dump do banco de dados '{database}' criado com sucesso no arquivo '{dump_file}'")
    except mysql.connector.Error as err:
        print(f"Erro ao criar o dump do banco de dados: {err}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    host = "localhost"
    user = "root"
    password = "root"
    database = "lgpd_db"

    dump_database_via_connection(host, user, password, database)
