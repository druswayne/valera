import shutil
import os

# Создаем папку static/animation если её нет
os.makedirs('static/animation', exist_ok=True)

# Копируем файлы
files_to_copy = ['style.css', 'script.js', 'box.png', 'valera.png', 'peshhera.png', 'reshetka.png']
for file in files_to_copy:
    if os.path.exists(file):
        shutil.copy2(file, f'static/{file}')
        print(f'Скопирован: {file}')

# Копируем папку animation
if os.path.exists('animation'):
    for subfolder in ['ilde', 'evil', 'run']:
        src = f'animation/{subfolder}'
        dst = f'static/animation/{subfolder}'
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f'Скопирована папка: {src}')

print('Копирование завершено!')

