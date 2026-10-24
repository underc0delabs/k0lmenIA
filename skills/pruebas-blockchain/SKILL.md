---
name: pruebas-blockchain
description: El cómo de probar blockchain/Web3 y smart contracts — testnets y nodos locales, funcional del contrato, tokens (ERC-20/721/1155), gas, seguridad (reentrancy, control de acceso, MEV, oráculos, proxies), firmas, integración dApp y Hardhat/Foundry/Slither. Lo usa el probador-blockchain.
---

# Pruebas de blockchain / Web3 y smart contracts

Un smart contract es **inmutable una vez desplegado** y maneja **valor real**: un bug no se "parchea" como en una app normal y puede costar fondos. Por eso se prueba con una exigencia alta, en **testnets o nodos locales**, nunca con fondos reales en mainnet para QA. Lo relacionado a seguridad profunda se coordina con `analista-seguridad` / un auditor.

## 1. Redes y entornos

- **Nunca mainnet con fondos reales** para QA. Se usa una **testnet** (Sepolia, Holesky) con faucets, o un **nodo local** (Hardhat Network, Foundry/Anvil, Ganache).
- **Forking de mainnet**: correr una copia local del estado real para probar integraciones (con protocolos ya desplegados) sin gastar.
- Confirmá la **cadena** (Ethereum/EVM, L2 como Arbitrum/Optimism/Polygon, u otra como Solana) y el **chain id**.

## 2. Funcional del contrato

- **view/pure** (leen, no cuestan gas al llamarlas off-chain) vs. las que **cambian estado** (transacciones, cuestan gas, emiten eventos).
- **Eventos/logs**: cada acción importante emite el evento correcto con los parámetros correctos (la dApp y los indexadores dependen de ellos).
- **require/revert y custom errors**: las precondiciones se validan y revierten con el motivo correcto; probá que una operación inválida **revierta** (no que falle silenciosa ni que deje estado a medias).
- **Valores de retorno** y cambios de estado coherentes.

## 3. Tokens y estándares

- **ERC-20**: `transfer`, `transferFrom`, `approve`/`allowance`, **decimales** (no asumir 18), balances, eventos `Transfer`/`Approval`; el patrón approve→transferFrom y el riesgo del approve infinito.
- **ERC-721 / ERC-1155** (NFTs): propiedad, `safeTransfer`, metadata/tokenURI, aprobaciones por operador.

## 4. Gas

- **Estimación** y límites; qué pasa con **out-of-gas** (revierte, no deja estado a medias); operaciones que escalan con el tamaño (loops sobre arrays sin límite → DoS por gas).
- **Gas reporting** para detectar funciones caras.

## 5. Seguridad de smart contracts

Lo más crítico (coordinar con un auditor para lo profundo):

- **Reentrancy**: una llamada externa antes de actualizar el estado permite re-entrar y drenar fondos (patrón checks-effects-interactions, reentrancy guard).
- **Control de acceso**: funciones sensibles con `onlyOwner`/roles; que un usuario común no pueda llamarlas; ownership transfer.
- **Overflow/underflow** (mitigado en Solidity ≥0.8, pero revisar unchecked).
- **Front-running / MEV**: transacciones que se pueden adelantar (approve, subastas); commit-reveal donde aplique.
- **Oráculos**: precios manipulables (usar TWAP, no spot); dependencia de un solo oráculo.
- **delegatecall** y **proxies** mal inicializados; **randomness** on-chain predecible (no usar `block.timestamp`/`blockhash` para sorteos).
- **DoS**: una cuenta que bloquea una cola, loops sin límite.

## 6. Upgradeabilidad

- **Proxies** (UUPS, Transparent): el **storage layout** no debe romperse entre versiones (no reordenar variables); la función de inicialización no se puede llamar dos veces; solo quien debe puede actualizar.

## 7. Firmas y permisos

- **EIP-712** (firmas tipadas), **permit** (ERC-2612): que una firma no se pueda **reusar** (replay) ni usar en otra cadena (chain id en el dominio); expiración de la firma.

## 8. Integración dApp ↔ contrato

- La **wallet** (MetaMask): conexión, cambio de cuenta y de red, rechazo de la firma; la dApp maneja bien un **revert** (muestra el error), una tx **pendiente** y las **confirmaciones**.
- **Reorg** (una tx confirmada que se revierte), **nonce** y **chain id** correctos; no asumir que una tx enviada ya está minada.

## 9. Automatizar

- **Hardhat** o **Foundry**: unit tests, **fuzzing** (Foundry/echidna) e **invariantes** (propiedades que siempre deben valer, p. ej. "la suma de balances = total supply"); **cobertura** y **gas report**.
- **Análisis estático**: Slither, Mythril (coordinar con `analista-codigo-seguro` para el enfoque SAST).
- La dApp (frontend) se prueba con Playwright + una wallet de prueba en testnet.

## 10. Bugs típicos de smart contracts

- **Reentrancy** que permite drenar fondos.
- Función sensible sin control de acceso (cualquiera puede llamar `withdraw`/`mint`).
- Asumir 18 decimales en un token que usa otros.
- Operación que no revierte ante una precondición inválida y deja estado inconsistente.
- Firma reutilizable (sin nonce/expiración/chain id) → replay.
- Proxy con storage layout roto tras un upgrade; inicializador llamado dos veces.
- Precio tomado del spot de un AMM (manipulable) en vez de un TWAP.
- Loop sobre un array que crece → out-of-gas / DoS.

## 11. Preguntas típicas para el equipo

Cuando no está escrito, son `FI-XX`:

- ¿Qué cadena/red y sobre qué testnet o nodo local se prueba? ¿Chain id?
- ¿Tenés el código fuente, la ABI y las direcciones desplegadas de QA?
- ¿El contrato es upgradeable (proxy)? ¿Quién puede actualizar?
- ¿Qué invariantes de negocio siempre deben cumplirse?
- ¿Hubo auditoría de seguridad? ¿Qué quedó pendiente?
- ¿Qué estándares de token implementa y con qué decimales?
