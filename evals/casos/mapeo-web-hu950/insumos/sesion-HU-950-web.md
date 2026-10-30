# Bitácora de la sesión de Playwright · HU-950 · staging (https://staging.tienda-eval.com)

Modo: headless (server playwright-headless). Usuario de prueba: APP_USER del .env.

## CP-001 · Login con credenciales válidas

1. browser_navigate https://staging.tienda-eval.com/login
   Snapshot:
   - heading "Iniciá sesión" [level=1]
   - textbox "Email" [placeholder="tu@email.com"]
   - textbox "Contraseña"
   - button "Ingresar"
   - link "¿Olvidaste tu contraseña?"
2. browser_type textbox "Email" ← qa.ana@tienda-eval.com
3. browser_type textbox "Contraseña" ← Clave$Eval2026
4. browser_click button "Ingresar"
   Snapshot:
   - banner: text "Hola, Ana"; button "Mi cuenta"; button "Salir"
   Resultado: coincide con el caso.

## CP-002 · Login con contraseña incorrecta

1. browser_navigate /login (mismo snapshot)
2. browser_type textbox "Email" ← qa.ana@tienda-eval.com
3. browser_type textbox "Contraseña" ← incorrecta
4. browser_click button "Ingresar"
   Snapshot:
   - alert "Credenciales inválidas"
   Resultado: el caso espera "Usuario o contraseña incorrectos"; la app muestra "Credenciales inválidas".

## CP-003 · Recordar la sesión

1. browser_navigate /login (mismo snapshot)
   No hay ningún checkbox "Recordarme" ni similar en la pantalla (se revisó el snapshot completo y el formulario después de hacer scroll).
   Resultado: no se pudo ejecutar el paso "marco Recordarme".

## CP-004 · Bloqueo por intentos fallidos

No se recorrió: depende de FI-01 (cantidad de intentos) y bloquear la cuenta de prueba en staging afecta al resto del equipo.

browser_close
