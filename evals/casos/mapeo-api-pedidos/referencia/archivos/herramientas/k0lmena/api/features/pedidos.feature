@contrato-pedidos @api @modulo-pedidos
Feature: API de pedidos (contrato 1.4.0)

  @CP-API-001 @alta @regresion @smoke
  Scenario: Listar pedidos pagados
    Given el request usa el token de autenticación
    And el request tiene los parámetros:
      | estado | pagado |
    When envío un GET a "/pedidos"
    Then el status de la respuesta es 200
    And la respuesta es una lista

  @CP-API-002 @alta @regresion
  Scenario: Listar pedidos sin token
    Given el request no envía token de autenticación
    When envío un GET a "/pedidos"
    Then el status de la respuesta es 401

  # La API responde total como string ("1500.00"); la spec dice number
  @CP-API-003 @media @regresion @difiere-de-la-spec
  Scenario: Detalle de un pedido
    Given el request usa el token de autenticación
    When envío un GET a "/pedidos/1201"
    Then el status de la respuesta es 200
    And el campo "total" de la respuesta es de tipo "number"

  @CP-API-004 @media @regresion
  Scenario: Detalle de un pedido que no existe
    Given el request usa el token de autenticación
    When envío un GET a "/pedidos/999999"
    Then el status de la respuesta es 404

  # FALTA INFORMACIÓN (FI-01): la spec no dice qué responde la API con un estado fuera de la lista
  # BLOQUEADO: falta información FI-01
  @CP-API-005 @media @falta-info @FI-01 @bloqueado
  Scenario: Listar pedidos con un estado inválido
    Given el request usa el token de autenticación
    And el request tiene los parámetros:
      | estado | cancelado |
    When envío un GET a "/pedidos"
    Then el status de la respuesta es 400

  # BLOQUEADO: sin verificar, método con efecto sin autorización
  @CP-API-006 @alta @bloqueado
  Scenario: Crear un pedido
    Given el request usa el token de autenticación
    When envío un POST a "/pedidos" con el body:
      """
      {"productos": [10, 11]}
      """
    Then el status de la respuesta es 201

  # BLOQUEADO: sin verificar, método con efecto sin autorización
  @CP-API-007 @alta @bloqueado
  Scenario: Cancelar un pedido
    Given el request usa el token de autenticación
    When envío un DELETE a "/pedidos/1201"
    Then el status de la respuesta es 204
