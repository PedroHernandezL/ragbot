# 🤖 Telegram RAG Bot

Bot de Telegram con capacidades RAG (Retrieval Augmented Generation) que permite hacer consultas inteligentes sobre documentos PDF usando OpenAI y PostgreSQL con pgvector.

## 🚀 Características

- **Bot de Telegram interactivo** con comandos personalizados
- **Procesamiento de documentos PDF** con extracción automática de texto
- **Búsqueda semántica** usando embeddings de OpenAI
- **Base de datos vectorial** con PostgreSQL + pgvector
- **API REST** para gestión de documentos y consultas
- **Almacenamiento de conversaciones** para contexto histórico
- **Docker** para fácil deployment
- **Compatible con Render** para hosting gratuito

## 🛠️ Tecnologías

- **Python 3.10.18**
- **FastAPI** - Framework web moderno
- **python-telegram-bot** - Wrapper para Telegram Bot API
- **OpenAI** - Embeddings y generación de respuestas
- **PostgreSQL + pgvector** - Base de datos vectorial
- **Neon** - Base de datos PostgreSQL serverless
- **SQLAlchemy** - ORM para Python
- **Docker** - Containerización

## 📋 Prerequisitos

- Python 3.10.18
- Token de bot de Telegram
- API Key de OpenAI
- Base de datos Neon PostgreSQL (o cualquier PostgreSQL con pgvector)

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd telegram-rag-bot
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=tu_token_de_bot

# OpenAI
OPENAI_API_KEY=tu_api_key_de_openai

# Database
DATABASE_URL=postgresql://username:password@endpoint/dbname?sslmode=require

# Configuración opcional
DEBUG=False
LOG_LEVEL=INFO
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_TOKENS=500
TEMPERATURE=0.7
```

### 3. Instalación local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python -m uvicorn src.main:app --reload
```

### 4. Usando Docker

```bash
# Construir y ejecutar con Docker Compose
docker-compose up --build

# Solo Docker
docker build -t telegram-rag-bot .
docker run -p 8000:8000 --env-file .env telegram-rag-bot
```

## 🚀 Deployment en Render

### Opción 1: Deploy desde GitHub

1. Conecta tu repositorio GitHub a Render
2. Crea un nuevo **Web Service**
3. Selecciona **Docker** como runtime
4. Configura las variables de entorno en el dashboard de Render
5. Deploy automático

### Opción 2: Docker Hub

```bash
# Construir y subir imagen
docker build -t tu-usuario/telegram-rag-bot:latest .
docker push tu-usuario/telegram-rag-bot:latest

# En Render, usar: tu-usuario/telegram-rag-bot:latest
```

### Variables de entorno en Render

```
TELEGRAM_BOT_TOKEN=tu_token
OPENAI_API_KEY=tu_api_key  
DATABASE_URL=tu_conexion_neon
DEBUG=False
LOG_LEVEL=INFO
```

## 📚 Uso

### Bot de Telegram

1. **Iniciar el bot**: `/start`
2. **Obtener ayuda**: `/help`  
3. **Hacer pregunta**: Envía cualquier mensaje de texto

### API REST

#### Subir documento PDF
```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@documento.pdf"
```

#### Hacer consulta
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d "{\"query\":\"¿Cuál es el tema principal del documento?\"}"
```

#### Listar documentos
```bash
curl -X GET "http://localhost:8000/api/v1/documents" \
     -H "accept: application/json"
```

#### Estadísticas
```bash
curl -X GET "http://localhost:8000/api/v1/stats" \
     -H "accept: application/json"
```

## 🏗️ Estructura del proyecto

```
telegram-rag-bot/
├── src/
│   ├── api/
│   │   └── endpoints.py       # Endpoints de FastAPI
│   ├── bot/
│   │   └── telegram_bot.py    # Lógica del bot de Telegram
│   ├── database/
│   │   └── connection.py      # Configuración de base de datos
│   ├── models/
│   │   └── database.py        # Modelos SQLAlchemy
│   ├── services/
│   │   ├── openai_service.py  # Servicio OpenAI
│   │   └── rag_service.py     # Lógica RAG
│   └── main.py               # Aplicación principal
├── config/
│   └── settings.py           # Configuración
├── data/                     # Directorio para PDFs
├── requirements.txt          # Dependencias Python
├── Dockerfile               # Configuración Docker
├── docker-compose.yml       # Orquestación Docker
├── .env.example            # Variables de entorno ejemplo
└── README.md               # Este archivo
```

## 🔍 Funcionalidades detalladas

### 🤖 Bot de Telegram

- **Registro automático** de usuarios
- **Historial de conversaciones** para contexto
- **Respuestas contextuales** usando RAG
- **Comandos interactivos** (/start, /help)
- **Manejo de errores** robusto

### 📄 Procesamiento de PDFs

- **Extracción de texto** usando pdfplumber y PyPDF2
- **Chunking inteligente** de documentos
- **Generación de embeddings** con OpenAI
- **Almacenamiento vectorial** en PostgreSQL

### 🔍 Sistema RAG

- **Búsqueda semántica** por similaridad vectorial
- **Recuperación de contexto** relevante
- **Generación de respuestas** con GPT-3.5-turbo
- **Combinación de información** de múltiples fuentes

## 🛠️ Configuración de base de datos

### Neon PostgreSQL

1. Crear cuenta en [Neon](https://neon.tech)
2. Crear nuevo proyecto
3. Habilitar extensión pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Copiar string de conexión

### PostgreSQL local

```sql
-- Crear base de datos
CREATE DATABASE telegram_bot;

-- Habilitar pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

## 🔒 Seguridad

- Variables de entorno para credenciales
- Validación de tipos de archivo
- Sanitización de inputs
- Logs de auditoría
- Límites de rate en producción

## 📊 Monitoreo

- **Logs estructurados** con diferentes niveles
- **Métricas de uso** via endpoint /stats
- **Health checks** via endpoint /health
- **Monitoreo de errores** en logs

## 🚨 Troubleshooting

### Error de conexión a base de datos
```bash
# Verificar string de conexión
echo $DATABASE_URL

# Testear conexión
python -c "import asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

### Bot no responde
```bash
# Verificar token
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Revisar logs
docker logs telegram-rag-bot
```

### Problemas con embeddings
```bash
# Verificar API key de OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/models"
```

## 📝 TODO

- [ ] Soporte para más tipos de documentos (Word, Excel)
- [ ] Interfaz web para administración
- [ ] Sistema de usuarios y permisos
- [ ] Métricas avanzadas con Prometheus
- [ ] Tests unitarios y de integración
- [ ] Cache de respuestas frecuentes
- [ ] Soporte multiidioma

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes preguntas o necesitas ayuda:

1. Revisa la documentación
2. Busca en los issues existentes
3. Crea un nuevo issue con detalles del problema

---

**¡Listo para empezar!** 🚀

Sigue las instrucciones de instalación y tendrás tu bot RAG funcionando en minutos.