@HU-950 @web @modulo-login
Feature: Inicio de sesión en la tienda

  Background:
    Given que estoy en la página de inicio de sesión

  @CP-001 @positivo @smoke
  Scenario: Login con credenciales válidas
    When ingreso el usuario y la contraseña del ambiente
    And presiono el botón "Ingresar"
    Then veo el saludo "Hola, Ana"

  # Posible bug: la app muestra "Credenciales inválidas"; el Then queda como dice el caso.
  @CP-002 @negativo
  Scenario: Login con contraseña incorrecta
    When ingreso el usuario del ambiente y la contraseña "incorrecta"
    And presiono el botón "Ingresar"
    Then veo el mensaje "Usuario o contraseña incorrectos"

  # Bloqueado: no existe el checkbox "Recordarme" en la pantalla de login.
  @CP-003 @positivo @bloqueado
  Scenario: Recordar la sesión
    When ingreso el usuario y la contraseña del ambiente
    And marco "Recordarme"
    And presiono el botón "Ingresar"
    Then al volver a abrir la tienda sigo logueado

  # FALTA INFORMACIÓN (FI-01): no está definido después de cuántos intentos fallidos se bloquea la cuenta
  @CP-004 @negativo @falta-info @FI-01 @bloqueado
  Scenario: Bloqueo por intentos fallidos
    When ingreso una contraseña incorrecta 5 veces
    Then veo el mensaje "Tu cuenta fue bloqueada temporalmente"
