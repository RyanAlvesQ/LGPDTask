# Arquivo: backup_functions.py

import shutil
import os

def backup(source_directory, destination_directory):
    try:
        # Verifica se o diretório de destino existe
        if os.path.exists(destination_directory):
            # Se o diretório de destino existe como arquivo, exclua-o
            if os.path.isfile(destination_directory):
                os.remove(destination_directory)
            # Se o diretório de destino existe como diretório, exclua seu conteúdo
            elif os.path.isdir(destination_directory):
                shutil.rmtree(destination_directory)

        # Copia recursivamente os arquivos do diretório de origem para o diretório de destino
        shutil.copytree(source_directory, destination_directory)
        print(f"Backup concluído com sucesso de {source_directory} para {destination_directory}")
    except Exception as e:
        print(f"Erro durante o backup: {e}")
