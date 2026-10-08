// Stubs mínimos para compilar con TS (no son los tipos oficiales; k6 resuelve los módulos en runtime)

declare module 'k6' {
  export function sleep(seconds: number): void;
  export function check<T = any>(value: T, checks: Record<string, (val: T) => boolean>, tags?: Record<string, string>): boolean;
  export function group<T>(name: string, fn: () => T): T;
  export function fail(message?: string): never;
}

declare module 'k6/http' {
  export interface Params {
    headers?: Record<string, string>;
    tags?: Record<string, string>;
    timeout?: string | number;
  }
  export interface Response {
    status: number;
    body: any;
    headers: Record<string, string>;
    timings: Record<string, number>;
    json(selector?: string): any;
  }

  const http: {
    request(method: string, url: string, body?: any, params?: Params): Response;
    get(url: string, params?: Params): Response;
    post(url: string, body?: any, params?: Params): Response;
    put(url: string, body?: any, params?: Params): Response;
    patch(url: string, body?: any, params?: Params): Response;
    del(url: string, body?: any, params?: Params): Response;
  };

  export default http;
}
