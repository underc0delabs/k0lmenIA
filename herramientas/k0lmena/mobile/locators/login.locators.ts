// mobile/locators/login.locators.ts
export const loginLocators = {
    // Usa UIAutomator para buscar el elemento con resourceId "emailInput"
    userField: 'android=new UiSelector().resourceId("emailInput")',
    
    // Para el campo contraseña, de forma similar:
    passwordField: 'android=new UiSelector().resourceId("passwordInput")',
    
    // Botón de iniciar sesión; aquí usamos accessibility id
    loginButton: '~Iniciar sesión',
    
    // Elemento de confirmación en la pantalla principal (ajustalo según tu app)
    homeScreen: 'android=new UiSelector().textContains("credencial")'
  };
  