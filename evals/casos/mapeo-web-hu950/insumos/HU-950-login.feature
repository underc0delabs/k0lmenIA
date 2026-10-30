@HU-950 @modulo-login
Feature: Inicio de sesión en la tienda

  Background:
    Given que estoy en la página de inicio de sesión

  @CP-001 @positivo @smoke
  Scenario: Login con credenciales válidas
    When ingreso el usuario y la contraseña válidos
    And presiono "Ingresar"
    Then veo el saludo "Hola, Ana"

  @CP-002 @negativo
  Scenario: Login con contraseña incorrecta
    When ingreso el usuario válido y la contraseña "incorrecta"
    And presiono "Ingresar"
    Then veo el mensaje "Usuario o contraseña incorrectos"

  @CP-003 @positivo
  Scenario: Recordar la sesión
    When ingreso el usuario y la contraseña válidos
    And marco "Recordarme"
    And presiono "Ingresar"
    Then al volver a abrir la tienda sigo logueado

  # FALTA INFORMACIÓN (FI-01): no está definido después de cuántos intentos fallidos se bloquea la cuenta
  @CP-004 @negativo @falta-info @FI-01
  Scenario: Bloqueo por intentos fallidos
    When ingreso una contraseña incorrecta 5 veces
    Then veo el mensaje "Tu cuenta fue bloqueada temporalmente"
