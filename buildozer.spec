[app]

title = Pong Game
package.name = ponggame
package.domain = org.mypong

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy

orientation = landscape
fullscreen = 1

# آیکون و صفحه لودینگ اختیاری هستن، در صورت داشتن فایل عکس، مسیرشون رو اینجا بدید
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
