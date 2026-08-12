# carmensay

Como `cowsay`, pero con Carmen Gloria. Un script de Python sin dependencias que
imprime un globo de diálogo sobre un retrato en ASCII.

![preview](carmensay-preview.png)

## Uso

```bash
python3 carmensay.py "Hola, buenas tardes"
echo "texto por tubería" | python3 carmensay.py
git log -1 --format=%s | python3 carmensay.py -s
```

## Opciones

| Flag | Qué hace |
|---|---|
| `-s`, `--small` | retrato compacto, 40 columnas |
| `-b`, `--big` | retrato detallado, 76 columnas |
| `-c`, `--color` | bloques + truecolor: casi la foto |
| `-a`, `--ansi` | caracteres ASCII + truecolor |
| `-n`, `--no-color` | monocromo, ASCII clásico |
| `-t`, `--think` | globo de pensamiento |
| `-W N` | ancho del texto (por defecto 40) |
| `--plain` | solo el retrato, sin globo |

Sin flags elige solo: color con bloques si la salida es un terminal compatible,
monocromo si se redirige a un archivo o tubería. Respeta `NO_COLOR`. El tamaño
se ajusta al ancho del terminal (compacto bajo 80 columnas).

El modo `-c` necesita un terminal con truecolor (24 bits): iTerm2, Kitty,
Alacritty, WezTerm, GNOME Terminal, Windows Terminal. Si se ve mal, usa `-a`.

## Instalar como comando

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/carmensay.py" ~/.local/bin/carmensay
# asegúrate de que ~/.local/bin esté en tu PATH
carmensay "ya funciona"
```

### Compilar a binario standalone

Se puede generar un binario sin dependencias con PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "carmen_gloria.blob:." carmensay.py
```

El binario queda en `dist/carmensay`. Copialo a cualquier carpeta del `PATH` y
listo — no necesita Python, Pillow ni el blob suelto.

```bash
sudo cp dist/carmensay /usr/local/bin/
carmensay "Hola desde un binario"
```

El código usa `sys._MEIPASS` para encontrar el blob dentro del bundle, y como
fallback lee el archivo suelto del directorio del script en modo desarrollo.

Para que salude al abrir la terminal, agrega a `~/.bashrc` o `~/.zshrc`:

```bash
carmensay -s "Buenos días, $USER"
```

## Cambiar la foto

`regenerar.py` reconstruye el arte embebido dentro de `carmensay.py`. Necesita
`pillow` y `numpy`.

```bash
pip install pillow numpy
python3 regenerar.py otra_foto.png --crop 545 60 880 560
```

Funciona mejor con un PNG de fondo transparente: el canal alfa se usa para
recortar la silueta. Con `--no-crop` toma la imagen completa; `--big` y
`--small` cambian el ancho en columnas de cada versión.

## Archivos

- `carmensay.py` — el script (arte incluido, sin dependencias)
- `regenerar.py` — regenera el arte desde otra imagen
- `carmen-gloria-ascii-76col.txt` / `-40col.txt` — el retrato en texto plano
- `carmensay-preview.png` — los tres modos lado a lado
