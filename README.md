# DeZoio — MVP Ideathon

> Identidade visual e fluxo baseados no protótipo DeZoio (`dezoio/`), ligados
> no backend real. UI 100% offline (Tailwind/Lucide vendorizados em
> `app/static/vendor/`). Fluxo: **/** (seleção de ambiente) → **/painel**
> (Dashboard com feed ao vivo + stats + Automação com wizard de 5 etapas que
> treina perfil e cria regra reais) → telas de gestão (/pessoas, /objetos,
> /regras).

A câmera vira fonte de dados: reconhecimento facial + detecção de objetos em tempo
real alimentam **eventos** e um **construtor de regras SE → ENTÃO**. Tudo roda
**local e offline** (Apple Silicon, sem nuvem).

- **Reconhecimento facial**: InsightFace (RetinaFace + ArcFace). "Treinar" uma
  pessoa = enviar 3–5 fotos; o reconhecimento vale na hora.
- **Objetos**: YOLO-World open-vocabulary — vocabulário amplo pré-configurado
  (capacete, garrafa, celular, cachorro...), ajustável por texto, sem treino.
- **Regras**: SE [pessoa reconhecida / desconhecido / objeto detectado /
  pessoa COM-SEM objeto / objeto ausente] ENTÃO [banner verde/vermelho + som].

## Como rodar (dia da demo)

```bash
cd iot-vision
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# abrir http://localhost:8000
```

Não precisa de internet (modelos já baixados em ~/.insightface e ~/.cache).
A primeira execução pede permissão de câmera pro app do terminal.

## Setup numa máquina nova (macOS ou Linux)

Os modelos (~4,5 GB) não vão pro git — ficam em caches do usuário e baixam
sob demanda:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/download_models.py   # baixa buffalo_l + YOLO-World + CLIP (precisa de internet)
.venv/bin/uvicorn app.main:app --port 8000
```

- **buffalo_l** (facial) → `~/.insightface/models/` (baixa no primeiro uso)
- **yolov8l-worldv2.pt** → raiz do projeto (a ultralytics baixa sozinha)
- **CLIP** (encoder de texto do YOLO-World) → cache da ultralytics
- **LocateAnything-3B** (opcional) → cache do Hugging Face; requer
  `pip install -r requirements-locate.txt` — **só macOS/Apple Silicon**.
  Em Linux, use o backend padrão (YOLO); o suporte CUDA ao Locate é roadmap.

Em Linux, a webcam usa V4L2 pelo OpenCV — mesmo código, sem permissão de
câmera do macOS pra conceder.

### Backend de objetos alternativo (experimental)

```bash
OBJECT_BACKEND=locate .venv/bin/uvicorn app.main:app --port 8000
```

Usa o **NVIDIA LocateAnything-3B** rodando local via MLX em vez do YOLO-World.
É um VLM de 3B parâmetros: caixas mais "inteligentes", porém atualizam a cada
alguns segundos (o vídeo continua fluido). Atenção: licença NVIDIA apenas para
pesquisa/não-comercial — serve para demo/comparação, não para o produto.
O padrão (sem a flag) continua sendo o YOLO-World, em tempo real.

Aguarde os chips "Reconhecimento facial" e "Detecção de objetos" ficarem verdes
(~10 s carregando modelos).

## Roteiro sugerido do pitch

1. **Ao Vivo**: aparecer na câmera → "ACESSO LIBERADO — {nome}" (regra, não hardcode).
2. Chamar alguém não cadastrado → "PESSOA NÃO RECONHECIDA".
3. **Pessoas**: cadastrar essa pessoa ao vivo (capturar da câmera) → reconhecida na hora.
4. Mostrar objetos (garrafa, celular...) → eventos aparecem sem configurar nada.
5. **Regras**: criar uma regra ao vivo (ex.: garrafa ausente → "buscar água"),
   tirar a garrafa da cena → alerta dispara em ~5 s.
6. Colocar/tirar o boné → "{nome} SEM BONÉ" (demonstra o caso de uso EPI com identidade;
   no discurso, é o mesmo mecanismo para capacete/colete/máscara em ambiente industrial).

## Estrutura

```
app/
  main.py     rotas FastAPI (páginas, MJPEG /video_feed, SSE /events, APIs)
  camera.py   thread de captura + threads de inferência (rosto e objetos)
  faces.py    InsightFace: embeddings e match por cosseno (threshold 0.40)
  objects.py  YOLO-World: vocabulário por texto, MPS (GPU do Mac)
  rules.py    motor de regras SE→ENTÃO com período de carência anti-flicker
  events.py   log de eventos com cooldown de 10 s por chave
  store.py    persistência em data/db.json
  static/     UI dark (Ao Vivo, Pessoas, Regras) — HTML/JS puro
scripts/
  download_models.py  baixa/valida modelos (rodar com internet)
  camera_check.py     testa permissão de câmera
  test_pipeline.py    PoC em janela OpenCV
data/
  db.json             pessoas (embeddings), regras, configurações
  people/<id>/*.jpg   fotos de cadastro
```

Ajustes finos em `data/db.json > settings`: `face_threshold` (0.40 — suba para
menos falsos positivos, desça se não reconhecer) e `object_conf` (0.45).

## Roadmap (próxima etapa — citar no pitch como visão de produto)

- **Dashboard e analytics**: eventos/dia, precisão, horários de pico, economia estimada.
- **Múltiplas câmeras** (RTSP/IP): tela de câmeras com status, FPS e detalhe por câmera.
- **Construtor de regras em canvas** (estilo n8n): condições compostas E/OU, drag-and-drop.
- **Integrações**: WhatsApp, Slack, e-mail, webhooks, ERP.
- **Reconhecimento individual de animais** (hoje detecta a espécie; o indivíduo requer treino).
- **Produtos específicos do cliente**: fine-tune do YOLO com fotos reais.
