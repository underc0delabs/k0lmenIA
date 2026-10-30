// mobile/wdio-globals.d.ts
import type { 
    Element as WDIOElement, 
    ElementArray as WDIOElementArray, 
    Browser as WDIOBrowser 
  } from 'webdriverio';
  
  declare module '@wdio/cucumber-framework';
  
  declare global {
    const $: (selector: string) => Promise<WDIOElement>;
    const $$: (selector: string) => Promise<WDIOElementArray>;
    const browser: WDIOBrowser;
  }
  
  export {};
  