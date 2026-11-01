#!/usr/bin/env bash
# Instala o Recados para o usuário atual (idempotente).
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")" && pwd)"
APP_ID=io.github.joaowgf.Recados
UUID=recados@joaogazire

mkdir -p ~/.local/bin ~/.local/share/applications ~/.config/autostart ~/.local/share/gnome-shell/extensions

cat > ~/.local/bin/recados <<SH
#!/bin/sh
PYTHONPATH="$RAIZ" exec python3 -m recados "\$@"
SH
chmod +x ~/.local/bin/recados

cat > ~/.local/share/applications/$APP_ID.desktop <<DESK
[Desktop Entry]
Type=Application
Name=Recados
Comment=Post-its com Markdown
Exec=$HOME/.local/bin/recados
Icon=accessories-text-editor
Categories=Utility;
StartupNotify=false
DESK
sed "s|^Exec=.*|Exec=$HOME/.local/bin/recados --sessao|" ~/.local/share/applications/$APP_ID.desktop > ~/.config/autostart/$APP_ID.desktop

ln -sfn "$RAIZ/extensao/$UUID" ~/.local/share/gnome-shell/extensions/$UUID
python3 - "$UUID" <<'PY'
import ast, subprocess, sys
uuid = sys.argv[1]
atual = ast.literal_eval(subprocess.check_output(
    ["gsettings", "get", "org.gnome.shell", "enabled-extensions"], text=True).removeprefix("@as "))
if uuid not in atual:
    subprocess.check_call(["gsettings", "set", "org.gnome.shell", "enabled-extensions", str(atual + [uuid])])
PY

# Atalho global Super+Alt+N -> nova nota (acrescenta sem apagar os outros)
BASE=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/recados/
python3 - "$BASE" <<'PY'
import ast, subprocess, sys
base = sys.argv[1]
chave = "org.gnome.settings-daemon.plugins.media-keys"
atual = ast.literal_eval(subprocess.check_output(["gsettings", "get", chave, "custom-keybindings"], text=True).removeprefix("@as "))
if base not in atual:
    subprocess.check_call(["gsettings", "set", chave, "custom-keybindings", str(atual + [base])])
PY
S="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$BASE"
gsettings set "$S" name 'Recados: nova nota'
gsettings set "$S" command "$HOME/.local/bin/recados --nova"
gsettings set "$S" binding '<Super><Alt>n'

echo "Recados instalado. Saia e entre na sessão uma vez para o GNOME carregar a extensão."
