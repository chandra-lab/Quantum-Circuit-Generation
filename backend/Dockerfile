FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CPU PyTorch is for later research imports. Simulation uses Qiskit Aer only.
# The import below fails the image build if torch or Aer cannot be imported.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "torch==2.6.0+cpu" --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import torch; print('torch', torch.__version__); import qiskit; from qiskit_aer import AerSimulator; AerSimulator(); print('quantum-ok')"

COPY app ./app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/mpl \
    && chmod 1777 /tmp/mpl
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
