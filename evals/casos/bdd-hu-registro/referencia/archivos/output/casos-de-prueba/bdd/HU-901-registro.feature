@HU-901
Feature: Registro de cuenta
  Como visitante de la tienda quiero crear una cuenta para comprar y seguir mis pedidos

  Background:
    Given la persona está en el formulario de registro

  @CP-001 @positivo
  Scenario: Registro con todos los datos válidos
    When completa nombre, email, usuario, contraseña y fecha de nacimiento válidos
    And envía el formulario
    Then se muestra "¡Cuenta creada! Revisá tu correo para activarla."

  @CP-002 @borde
  Scenario Outline: Largo del usuario en los límites
    When completa el usuario con "<usuario>"
    And envía el formulario
    Then el resultado es "<resultado>"

    Examples:
      | usuario               | resultado                                      |
      | abc                   | El usuario debe tener entre 4 y 20 caracteres  |
      | abcd                  | se crea la cuenta                              |
      | usuario_de_veinte_ch  | se crea la cuenta                              |
      | usuario_de_veintiuno_ | El usuario debe tener entre 4 y 20 caracteres  |

  @CP-003 @negativo
  Scenario: Email con formato inválido
    When completa el email con "ana.test.com"
    And envía el formulario
    Then no se crea la cuenta

  @CP-004 @positivo
  Scenario: Nombre con apóstrofe
    When completa el nombre con "Sean O'Connor"
    And envía el formulario
    Then se crea la cuenta

  # FALTA INFORMACIÓN (FI-01): el texto del error de email duplicado no está definido en el CA2.
  @CP-005 @negativo @falta-info @FI-01
  Scenario: Email ya registrado
    Given existe una cuenta con el email "ana@test.com"
    When completa el email con "ana@test.com"
    And envía el formulario
    Then no se crea la cuenta y se muestra un mensaje de error

  # FALTA INFORMACIÓN (FI-02): la edad mínima es 18 en la descripción y 16 en el CA4.
  @CP-006 @borde @falta-info @FI-02
  Scenario: Persona de 17 años
    When completa la fecha de nacimiento de alguien de 17 años
    And envía el formulario
    Then el resultado depende de la edad mínima que confirme el PO

  # FALTA INFORMACIÓN (FI-03): la contraseña "segura" del CA3 no tiene reglas.
  @CP-007 @negativo @falta-info @FI-03
  Scenario: Contraseña débil
    When completa la contraseña con "abc"
    And envía el formulario
    Then el resultado depende de las reglas de contraseña que confirme el PO
