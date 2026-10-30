import textos from '../i18n/es.json';

export const MAX_CUPONES_POR_COMPRA = 1;

export function aplicarCupon(carrito: { cupones: string[] }, codigo: string): string | null {
  if (carrito.cupones.length >= MAX_CUPONES_POR_COMPRA) return textos.cuponYaAplicado;
  carrito.cupones.push(codigo);
  return null;
}
