#!/usr/bin/env bash
set -euo pipefail

PY_VERSION="${PY_VERSION:-3.6.15}"
ENV_NAME="${ENV_NAME:-py36env}"
REQ_FILE="${REQ_FILE:-HiGitClass/requirements.txt}"
export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
export PATH="$PYENV_ROOT/bin:$PATH"

if ! command -v pyenv >/dev/null 2>&1; then
  echo "pyenv not found on PATH. Install pyenv and rerun." >&2
  exit 1
fi

# check for and enable virtualenv
eval "$(pyenv init -)"
if command -v pyenv-virtualenv-init >/dev/null 2>&1; then
  eval "$(pyenv virtualenv-init -)"
fi

echo "Installing Python ${PY_VERSION}"
pyenv install -s "$PY_VERSION"

echo "Creating virtualenv ${ENV_NAME}…"
# overwrite if exists
pyenv virtualenv -f "$PY_VERSION" "$ENV_NAME"
export PYENV_VERSION="$ENV_NAME"

echo "Installing build tooling…"
pyenv exec python -m pip install --upgrade "pip<22" "setuptools<60" "wheel<0.38"

if [[ -f "$REQ_FILE" ]]; then
  echo "Installing ${REQ_FILE}…"
  pyenv exec pip install -r "$REQ_FILE"
else
  echo "No ${REQ_FILE} found; skipping requirements installation."
fi

echo "Installing smart_open==1.9.0…"
pyenv exec pip install "smart_open==1.9.0"

# Make this env the local default in the current directory
pyenv local "$ENV_NAME"

cat <<EOF

Done.

Environment:     $ENV_NAME
Python version:  $PY_VERSION
Local setting:   .python-version now pins '$ENV_NAME' in this directory

Use it like:
  pyenv activate $ENV_NAME
  python -V
  pip list
EOF
