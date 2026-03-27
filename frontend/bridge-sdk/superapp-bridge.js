/**
 * Super App Mini-App Bridge SDK
 * 
 * This SDK is used by mini-apps to communicate with the host Super App shell.
 * It uses JSON-RPC 2.0 over window.postMessage for secure, asynchronous IPC.
 * 
 * Usage:
 * import SuperApp from './superapp-bridge.js';
 * const user = await SuperApp.getIdentity();
 */

class SuperAppBridge {
    constructor() {
      this.callbacks = new Map();
      this.id = 1;
  
      if (typeof window !== 'undefined') {
        window.addEventListener('message', (event) => {
          const { jsonrpc, id, result, error } = event.data || {};
          if (jsonrpc !== '2.0' || !id) return;
  
          if (this.callbacks.has(id)) {
            const { resolve, reject } = this.callbacks.get(id);
            this.callbacks.delete(id);
            if (error) {
              reject(new Error(error.message || 'Bridge Error'));
            } else {
              resolve(result);
            }
          }
        });
      }
    }
  
    _send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const requestId = this.id++;
        this.callbacks.set(requestId, { resolve, reject });
  
        const message = {
          jsonrpc: '2.0',
          id: requestId,
          method,
          params
        };
  
        if (window.parent) {
          window.parent.postMessage(message, '*');
        } else {
          reject(new Error('Parent shell not found. Bridge must run inside the Super App sandbox.'));
        }
      });
    }
  
    /**
     * identity.get
     * Returns the current user's identity metadata (respecting privacy boundaries)
     */
    async getIdentity() {
      return this._send('identity.get');
    }
  
    /**
     * payment.request
     * Triggers a payment authorization modal in the host shell.
     * @param {number} amount
     * @param {string} currency (e.g. "USD", "INR")
     * @param {string} memo
     */
    async requestPayment(amount, currency, memo = '') {
      return this._send('payment.request', { amount, currency, memo });
    }
  }
  
  const instance = new SuperAppBridge();
  export default instance;
