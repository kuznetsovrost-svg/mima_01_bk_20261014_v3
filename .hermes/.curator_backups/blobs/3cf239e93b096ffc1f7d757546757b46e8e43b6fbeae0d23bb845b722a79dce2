# Initial Prompts for Whisper

These text files are passed to Whisper as `initial_prompt` parameter. Whisper uses them to "warm up" the language model with relevant vocabulary, which significantly improves recognition accuracy for domain-specific terms.

## Available Prompts

| File | Use for | Vocabulary size |
|---|---|---|
| `ba_modeling.txt` | **BA modeling, IS design, requirements engineering** | ~1600 terms |
| `business_analysis.txt` | BA, project management, IT | ~700 terms |
| `bpmn.txt` | BPMN 2.0 lectures | ~650 terms |
| `it_programming.txt` | Programming, dev, IT ops | ~200 terms |
| `marketing_sales.txt` | Marketing, sales, e-commerce | ~460 terms |
| `medicine.txt` | Medicine, clinical practice | ~460 terms |
| `education.txt` | Pedagogy, education, edtech | ~490 terms |
| `hermes_agents.txt` | **Hermes, AI-agents, LLM infra** | ~700 terms |
| `general_russian.txt` | General Russian speech | minimal |

## How Whisper Uses initial_prompt

From [Whisper documentation](https://github.com/openai/whisper):

> The initial prompt is a way to provide context to Whisper about the expected content. It's especially useful for:
> - Domain-specific terminology (medical, legal, technical)
> - Proper names
> - Acronyms
> - Style hints

The prompt should:
1. Be **relevant vocabulary** (not full sentences)
2. Be **written naturally** (not in all caps)
3. **Include 100-500 terms** for best effect
4. Match the **language** of the audio

## Usage

```bash
# Via wrapper script
scripts/transcribe.sh lecture.mp3 --output ./out \
  --prompt "$(cat templates/initial_prompts/business_analysis.txt)"

# Via direct Python call
python3 scripts/full_pipeline.py lecture.mp3 --output ./out \
  --initial-prompt templates/initial_prompts/business_analysis.txt
```

## Creating Custom Prompts

For a new domain, create a file with:

1. **Topic description** (first sentence — context for Whisper)
2. **Terms and names** (separated by spaces or commas)
3. **Acronyms and abbreviations** (with expansions)
4. **Spelling variants** (both Latin and Cyrillic where applicable)

### Template

```
[Topic description in target language]

[Term1] [Term2] [Term3] [Acronym1: expansion] [Name1] [Name2] ...
```

### Example

```
Лекция по машинному обучению и data science.

ML, machine learning, глубокое обучение, deep learning, нейросеть,
neural network, CNN, RNN, LSTM, GRU, transformer, BERT, GPT, attention,
self-attention, encoder, decoder, embedding, токен, токенизация,
классификация, регрессия, кластеризация, градиентный спуск, gradient
descent, backpropagation, обратное распространение ошибки, SGD, Adam,
RMSProp, learning rate, batch size, epoch, эпоха, переобучение,
overfitting, underfitting, регуляризация, dropout, batch normalization,
train, val, test, train set, validation set, test set, метрика,
accuracy, precision, recall, F1, AUC, ROC, confusion matrix, матрица
ошибок, гиперпараметр, feature, признак, фича, target, таргет, label,
разметка, dataset, датасет, TensorFlow, PyTorch, scikit-learn, sklearn,
pandas, numpy, matplotlib, Jupyter, GPU, CUDA, обучение, inference,
вывод, предсказание, fine-tuning, дообучение, transfer learning,
трансферное обучение, MLOps, deployment, деплой модели, сериализация,
ONNX, TorchScript, model serving, REST API, FastAPI, gRPC, Kafka,
Airflow, MLflow, DVC, experiment tracking, трекинг экспериментов,
A/B тест, ab test, canary deployment, канареечный деплой, shadow
deployment, теневой режим, мониторинг модели, data drift, model drift,
concept drift, drift detection, переобучение, недообучение, баланс
классов, class imbalance, oversampling, undersampling, SMOTE, ансамбль,
ensemble, bagging, boosting, stacking, random forest, случайный лес,
gradient boosting, XGBoost, LightGBM, CatBoost, решающее дерево,
decision tree, кластеризация, k-means, DBSCAN, иерархическая
кластеризация, dimensionality reduction, понижение размерности, PCA,
t-SNE, UMAP, автоэнкодер, autoencoder, вариационный автоэнкодер, VAE,
generative adversarial network, GAN, генеративная состязательная сеть,
диффузионная модель, diffusion model, reinforcement learning,
обучение с подкреплением, агент, среда, награда, policy, стратегия,
Q-learning, actor-critic, A3C, PPO, exploration, exploitation,
разведка, эксплуатация, Markov decision process, марковский процесс
принятия решений, MCTS, Monte Carlo tree search, AlphaGo, AlphaZero,
prompt engineering, prompt engineering, fine-tuning, RAG, retrieval
augmented generation, vector database, векторная база данных,
embedding model, модель эмбеддингов, semantic search, семантический поиск.
```

## Best Practices

1. **Test the prompt**: try with and without, compare accuracy
2. **Don't overdo**: 200-500 terms is usually enough
3. **Match language**: Russian prompt for Russian audio
4. **Include proper names**: people, companies, tools
5. **Acronyms with expansions**: helps Whisper understand context
6. **Spelling hints**: include both correct and common misspellings
