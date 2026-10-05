# AI Multi-Database SQL Agent

## 1 A propos

## 2 Prérequis

### 2.1 Installer uv
`uv` est un gestionnaire de paquets Python moderne, écrit en Rust, qui remplace `pip` + `venv`.

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```


### 2.2 Configuration du modèle LLM

Le projet propose deux possibilités pour utiliser le modèle de langage : avec une clé API avec **Groq** ou en local avec **Ollama**.

### Option 1 — Groq

Groq permet d'utiliser un modèle de langage en ligne gratuitement, sans installer de modèle local.

1. Créez une clé API depuis [Groq API Keys](https://console.groq.com/keys).

```bash
# Windows (PowerShell)
git clone https://github.com/Hugo-Petit04/agent_Ia_Sql_multi-bases
cd agents_ia
uv sync
copy .env.groq .env
```
```bash
# macOS / Linux
git clone https://github.com/Hugo-Petit04/agent_Ia_Sql_multi-bases
cd agents_ia
uv sync
cp .env.groq .env
```

3. Ouvrez le fichier `.env`.
4. Remplacez `collez-votre-cle-groq-ici` par votre clé API.

### Option 2 - Ollama
Téléchargez Ollama depuis [ollama.com](https://ollama.com/), puis récupérez le modèle :

```bash
# Windows (PowerShell)
ollama pull qwen3.5:4b
git clone https://github.com/Hugo-Petit04/agent_Ia_Sql_multi-bases
cd agents_ia
uv sync
copy .env.ollama .env
```
```bash
# macOS / Linux
ollama pull qwen3.5:4b
git clone https://github.com/Hugo-Petit04/agent_Ia_Sql_multi-bases
cd agents_ia
uv sync
cp .env.ollama .env
```

## 3 Lancer l'agent

Ollama doit être lancé si on a choissi cette option

```bash
uv run streamlit run project/interface_Graphique.py
```
