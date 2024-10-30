import os
import time
import tmdbsimple as tmdb
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import socket

# Configurações
tmdb.API_KEY = 'eeee41dd5c435331be5827f514fc263a'  # Substitua pela sua chave da API do TMDB
service = Service('./chromedriver.exe')  # Certifique-se de ter o ChromeDriver correto no caminho

def iniciar_driver():
    while True:
        try:
            driver = webdriver.Chrome(service=service)
            driver.implicitly_wait(10)
            return driver
        except WebDriverException as e:
            log(f"Erro ao iniciar o WebDriver: {e}", "CRITICAL")
            time.sleep(60)

def verificar_conexao():
    while True:
        try:
            socket.create_connection(("www.google.com", 80))
            return True
        except OSError:
            log("Conexão de rede perdida. Aguardando reconexão...", "WARNING")
            time.sleep(30)

def carregar_filmes(arquivo="filmes.txt"):
    filmes = []
    try:
        with open(arquivo, "r", encoding="utf-8") as file:
            for linha in file:
                if '|' in linha:
                    nome, url = linha.strip().split("|")
                    filmes.append((nome, url))
        log(f"{len(filmes)} filmes carregados do arquivo '{arquivo}'.", "INFO")
    except FileNotFoundError:
        color_print(f"Erro: Arquivo '{arquivo}' não encontrado.", "red")
        log(f"Erro: Arquivo '{arquivo}' não encontrado.", "ERROR")
    return filmes

def carregar_filmes_adicionados(arquivo="adicionados.txt"):
    adicionados = set()
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as file:
            for linha in file:
                adicionados.add(linha.strip())
    return adicionados

def carregar_filmes_erro_slug(arquivo="erros_slug.txt"):
    erros_slug = set()
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as file:
            for linha in file:
                erros_slug.add(linha.strip())
    return erros_slug

def log(message, log_type="INFO"):
    with open("log_automation.txt", "a") as log_file:
        log_file.write(f"[{log_type}] {message}\n")
    print(f"[{log_type}] {message}")

def color_print(message, color="green"):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
    print(f"{colors[color]}{message}{colors['reset']}")

def login(driver, email, password):
    driver.get("https://seagreen-raven-413655.hostingersite.com/admin")
    log("Iniciando login...", "INFO")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login_email"))).send_keys(email)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login_password"))).send_keys(password)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "submit-btn"))).click()
        time.sleep(5)

        if "login" in driver.current_url:
            color_print("Login falhou, ainda na página de login.", "red")
            log("Login falhou, ainda na página de login.", "ERROR")
            return False
        else:
            color_print("Login realizado com sucesso!", "green")
            log("Login realizado com sucesso!", "SUCCESS")
            return True
    except TimeoutException:
        color_print("Falha ao realizar o login!", "red")
        log("Falha ao realizar o login!", "ERROR")
        return False

def buscar_id_filme(nome):
    search = tmdb.Search()
    response = search.movie(query=nome, language='pt-BR')
    if response['results']:
        movie_id = response['results'][0]['id']
        log(f"Filme '{nome}' encontrado com ID {movie_id}.", "INFO")
        return movie_id
    else:
        color_print(f"Filme '{nome}' não encontrado.", "yellow")
        log(f"Filme '{nome}' não encontrado.", "WARNING")
        return None

def esperar_mensagem_importacao(driver):
    try:
        WebDriverWait(driver, 30).until(
            EC.text_to_be_present_in_element((By.XPATH, "//div[contains(@class, 'alert-success')]"), "Data imported successfully.")
        )
        log("Mensagem 'Data imported successfully.' detectada.", "INFO")
        return True
    except TimeoutException:
        log("Mensagem 'Data imported successfully.' não detectada em 30 segundos.", "ERROR")
        return False

def adicionar_filme(driver, nome, url, i):
    movie_id = buscar_id_filme(nome)
    if not movie_id:
        return

    driver.get("https://seagreen-raven-413655.hostingersite.com/admin/videos_add/")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "imdb_id"))).send_keys(str(movie_id))
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'FETCH')]"))).click()
        
        if not esperar_mensagem_importacao(driver):
            return

        time.sleep(3)

        create_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn btn-primary') and contains(., 'Create')]"))
        )
        create_button.click()
        log("Botão 'Create' clicado após importação de dados.", "SUCCESS")

        try:
            ok_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'OK')]"))
            )
            ok_button.click()
            time.sleep(3)
            log("Botão 'OK' clicado.", "SUCCESS")
        except TimeoutException:
            log("Botão 'OK' não encontrado em 10 segundos.", "ERROR")

        if "This value is required." in driver.page_source:
            color_print(f"Filme '{nome}' ignorado devido a campo 'slug' não preenchido.", "yellow")
            log(f"Filme '{nome}' ignorado devido a campo 'slug' não preenchido.", "WARNING")
            with open("erros_slug.txt", "a", encoding="utf-8") as file:
                file.write(f"{nome}\n")
            return

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "label"))).send_keys(f"Server{i+1}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "order"))).send_keys(i + 1)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "url-input-field"))).send_keys(url)

        add_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'] span.btn-label"))
        )
        add_button.click()
        color_print(f"Filme '{nome}' adicionado com sucesso!", "green")
        log(f"Filme '{nome}' adicionado com sucesso!", "SUCCESS")
        
        with open("adicionados.txt", "a", encoding="utf-8") as file:
            file.write(f"{nome}\n")
            
    except Exception as e:
        color_print(f"Erro ao adicionar o filme '{nome}': {e}", "red")
        log(f"Erro ao adicionar o filme '{nome}': {e}", "ERROR")

def executar_script():
    driver = iniciar_driver()
    verificar_conexao()
    
    if not login(driver, "joaozinho449999@gmail.com", "9agos2010"):
        log("Login falhou. Tentando novamente em 60 segundos...", "ERROR")
        time.sleep(60)
        driver.quit()
        return executar_script()

    filmes = carregar_filmes()
    if not filmes:
        color_print("Nenhum filme para processar.", "yellow")
        log("Nenhum filme para processar.", "WARNING")
        return

    filmes_adicionados = carregar_filmes_adicionados()
    filmes_erro_slug = carregar_filmes_erro_slug()
    
    for i, (nome, url) in enumerate(filmes):
        if nome in filmes_adicionados or nome in filmes_erro_slug:
            log(f"Filme '{nome}' já foi adicionado anteriormente ou está marcado com erro de 'slug'. Pulando...", "INFO")
            continue
        
        color_print(f"Processando o filme '{nome}'...", "yellow")
        adicionar_filme(driver, nome, url, i)

    color_print("Script concluído.", "green")
    log("Script concluído.", "INFO")
    driver.quit()

if __name__ == "__main__":
    while True:
        try:
            executar_script()
        except Exception as e:
            log(f"Ocorreu um erro geral: {e}", "CRITICAL")
            time.sleep(60)
