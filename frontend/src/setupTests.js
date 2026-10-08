import { webcrypto } from 'crypto'
Object.defineProperty(global, 'crypto', { value: webcrypto, configurable: true })
