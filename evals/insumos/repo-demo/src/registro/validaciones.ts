import { z } from 'zod';
import textos from '../i18n/es.json';

export const registroSchema = z.object({
  nombre: z
    .string()
    .min(2)
    .max(50)
    .regex(/^[A-Za-zÁÉÍÓÚáéíóúÑñ' -]+$/),
  email: z.string().email(),
  usuario: z
    .string()
    .min(4, textos.usuarioLargo)
    .max(20, textos.usuarioLargo)
    .regex(/^[A-Za-z0-9_]+$/),
  password: z.string().min(8),
  fechaNacimiento: z.coerce.date(),
});

export const EDAD_MINIMA = 18;
