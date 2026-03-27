# RFC-003: Frontend Architecture and Mini-App Ecosystem

> **Status:** PROPOSED  
> **Author:** Principal Solutions Architect  
> **Created:** 2026-03-27  
> **Last Modified:** 2026-03-27  
> **Target Audience:** Frontend Engineering, Mobile Engineering, Developer Experience  
> **Depends On:** RFC-001 (IAM), RFC-002 (Payment Engine)

---

## 1. Abstract

This RFC defines the architecture for the Super App's frontend container and the Mini-App ecosystem. It specifies how the host application shell loads, isolates, and manages dynamically injected mini-apps (ride-hailing, food delivery, financial services, e-commerce, messaging) without App Store review cycles, while maintaining security boundaries, shared state, and a consistent user experience across platforms.

---

## 2. Existing System Baseline

The Super App frontend has already progressed significantly:

| Component | Current State | RFC Target |
|---|---|---|
| **Shell Host** | `frontend/shell/` — Vite + React, JWT state management | Full mobile-ready shell with native module federation |
| **Wallet MFE** | `frontend/wallet/` — Extracted as remote mini-app | Template for all future MFEs |
| **Shared UI** | `frontend/shared-ui/` — 7 components, Storybook v8, ES + UMD dist | Full design system SDK with theming API |
| **Module Federation** | Vite Module Federation (existing) | Extended with OTA versioning + rollback |
| **Mobile** | Planned (Phase 13: React Native / Expo) | React Native shell with WebView bridge |

---

## 3. Host App Architecture

### 3.1. Dual-Platform Shell Strategy

The Super App operates as **two synchronized shells** sharing the same mini-app ecosystem:

```
┌──────────────────────────────────────────────────────────────────┐
│                     SUPER APP ARCHITECTURE                        │
│                                                                    │
│  ┌─────────────────────────┐   ┌─────────────────────────────┐   │
│  │    WEB SHELL            │   │    MOBILE SHELL              │   │
│  │    (React + Vite)       │   │    (React Native + Expo)     │   │
│  │                         │   │                               │   │
│  │  ┌───────────────┐     │   │  ┌───────────────────┐       │   │
│  │  │ Module        │     │   │  │ Native Navigation │       │   │
│  │  │ Federation    │     │   │  │ (React Navigation)│       │   │
│  │  │ Runtime       │     │   │  └────────┬──────────┘       │   │
│  │  └───────┬───────┘     │   │           │                   │   │
│  │          │              │   │  ┌────────▼──────────┐       │   │
│  │  ┌───────▼───────┐     │   │  │ WebView Container │       │   │
│  │  │ Mini-App      │     │   │  │ (per Mini-App)    │       │   │
│  │  │ Container     │     │   │  │                   │       │   │
│  │  │ (iframe/      │     │   │  │ OTA Bundle Loader │       │   │
│  │  │  shadow DOM)  │     │   │  └────────┬──────────┘       │   │
│  │  └───────────────┘     │   │           │                   │   │
│  │                         │   │  ┌────────▼──────────┐       │   │
│  │  ┌───────────────┐     │   │  │ JS Bridge         │       │   │
│  │  │ State Bridge  │     │   │  │ (postMessage +    │       │   │
│  │  │ (CustomEvents)│     │   │  │  native modules)  │       │   │
│  │  └───────────────┘     │   │  └───────────────────┘       │   │
│  └─────────────────────────┘   └─────────────────────────────┘   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              SHARED INFRASTRUCTURE                          │   │
│  │                                                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │   │
│  │  │ Auth     │  │ Design   │  │ Analytics│  │ Mini-App  │ │   │
│  │  │ Context  │  │ System   │  │ SDK      │  │ Registry  │ │   │
│  │  │ Provider │  │ (shared- │  │ (OTel)   │  │ (Manifest)│ │   │
│  │  │          │  │  ui)     │  │          │  │           │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘ │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2. Web Shell — Module Federation Configuration

Extending the existing Vite Module Federation setup in `frontend/shell/`:

```javascript
// frontend/shell/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import federation from '@originjs/vite-plugin-federation';

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: 'superapp_shell',
      
      // Dynamic remotes — loaded from Mini-App Registry at runtime
      remotes: {
        // Static remotes (core mini-apps, always loaded)
        wallet_mfe: {
          external: `Promise.resolve(window.__MINI_APP_REGISTRY__?.wallet?.url || 'http://localhost:5001/assets/remoteEntry.js')`,
          from: 'vite',
          externalType: 'promise',
        },
      },
      
      // Shared dependencies — prevents duplicate React instances
      shared: {
        react: { singleton: true, requiredVersion: '^18.2.0' },
        'react-dom': { singleton: true, requiredVersion: '^18.2.0' },
        'react-router-dom': { singleton: true, requiredVersion: '^6.0.0' },
        '@superapp/shared-ui': { singleton: true },
        '@superapp/bridge-sdk': { singleton: true },
      },
    }),
  ],
  
  build: {
    modulePreload: false,
    target: 'esnext',
    minify: 'terser',
    cssCodeSplit: false,
  },
});
```

### 3.3. OTA Update Strategy (Bypassing App Store Review)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OTA UPDATE FLOW                                   │
│                                                                      │
│  ┌──────────────┐                                                    │
│  │ Developer    │                                                    │
│  │ pushes new   │                                                    │
│  │ mini-app     │                                                    │
│  │ version      │                                                    │
│  └──────┬───────┘                                                    │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐     ┌───────────────────┐                          │
│  │ CI/CD        │────►│ Mini-App Registry │                          │
│  │ Pipeline     │     │ (S3 + CloudFront) │                          │
│  │              │     │                   │                          │
│  │ • Build      │     │ manifest.json:    │                          │
│  │ • Test       │     │ {                 │                          │
│  │ • Sign       │     │   "wallet": {     │                          │
│  │ • Deploy     │     │     "version":    │                          │
│  │              │     │       "2.3.1",    │                          │
│  │              │     │     "url": "...", │                          │
│  │              │     │     "checksum":   │                          │
│  │              │     │       "sha384:.."}│                          │
│  │              │     │   }              │                          │
│  └──────────────┘     └───────┬───────────┘                          │
│                               │                                      │
│                               ▼                                      │
│  ┌──────────────────────────────────────────┐                        │
│  │ APP SHELL (on startup / background poll) │                        │
│  │                                          │                        │
│  │ 1. Fetch manifest.json (CDN cached 60s)  │                        │
│  │ 2. Compare versions with local cache     │                        │
│  │ 3. If new version:                       │                        │
│  │    a. Download bundle in background      │                        │
│  │    b. Verify SHA-384 checksum            │                        │
│  │    c. Swap on next navigation            │                        │
│  │    d. Show "Update available" toast      │                        │
│  │ 4. Rollback if crash detected:           │                        │
│  │    a. Track mini-app crash count         │                        │
│  │    b. If >3 crashes in 5 min → rollback  │                        │
│  │    c. Report to Sentry                   │                        │
│  └──────────────────────────────────────────┘                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Manifest Schema:**

```json
// https://cdn.superapp.global/mini-apps/manifest.json
{
  "schema_version": 2,
  "last_updated": "2026-03-27T16:00:00Z",
  "apps": {
    "wallet": {
      "name": "Wallet & Payments",
      "version": "2.3.1",
      "min_shell_version": "1.0.0",
      "bundle_url": "https://cdn.superapp.global/mini-apps/wallet/v2.3.1/remoteEntry.js",
      "bundle_checksum": "sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8w",
      "bundle_size_bytes": 284672,
      "permissions": ["wallet:read", "wallet:transfer", "camera", "notifications"],
      "regions": ["US", "EU", "INDIA"],
      "feature_flags": {
        "crypto_tab": false,
        "recurring_payments": true
      },
      "rollout": {
        "strategy": "canary",
        "percentage": 100,
        "previous_version": "2.3.0",
        "rollback_url": "https://cdn.superapp.global/mini-apps/wallet/v2.3.0/remoteEntry.js"
      }
    },
    "ride_hailing": {
      "name": "SuperRide",
      "version": "1.0.0",
      "min_shell_version": "1.0.0",
      "bundle_url": "https://cdn.superapp.global/mini-apps/ride/v1.0.0/remoteEntry.js",
      "bundle_checksum": "sha384-...",
      "bundle_size_bytes": 512000,
      "permissions": ["location:fine", "contacts:read", "notifications", "wallet:pay"],
      "regions": ["INDIA"],
      "feature_flags": {},
      "rollout": {
        "strategy": "full",
        "percentage": 100
      }
    },
    "food_delivery": {
      "name": "SuperEats",
      "version": "1.2.0",
      "min_shell_version": "1.0.0",
      "bundle_url": "https://cdn.superapp.global/mini-apps/food/v1.2.0/remoteEntry.js",
      "bundle_checksum": "sha384-...",
      "bundle_size_bytes": 620000,
      "permissions": ["location:fine", "wallet:pay", "notifications"],
      "regions": ["US", "EU", "INDIA"],
      "feature_flags": {
        "group_ordering": true,
        "live_tracking": true
      },
      "rollout": {
        "strategy": "canary",
        "percentage": 50
      }
    }
  }
}
```

### 3.4. Mobile Shell — React Native Architecture

```javascript
// frontend/mobile/App.tsx
import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { WebView } from 'react-native-webview';
import { MiniAppBridge } from '@superapp/mobile-bridge';
import { AuthProvider, useAuth } from '@superapp/auth-context';

const Tab = createBottomTabNavigator();

// Dynamic Mini-App loader via WebView
const MiniAppScreen = ({ route }) => {
  const { appId, bundleUrl } = route.params;
  const { accessToken, user } = useAuth();
  const bridge = new MiniAppBridge();

  const injectedJS = `
    window.__SUPERAPP_CONTEXT__ = {
      accessToken: '${accessToken}',
      userId: '${user.user_id}',
      region: '${user.region}',
      theme: 'dark',
      locale: '${user.locale}',
    };
    window.__SUPERAPP_BRIDGE__ = {
      postMessage: (msg) => window.ReactNativeWebView.postMessage(JSON.stringify(msg)),
    };
    true;
  `;

  return (
    <WebView
      source={{ uri: bundleUrl }}
      injectedJavaScriptBeforeContentLoaded={injectedJS}
      onMessage={(event) => bridge.handleMessage(event.nativeEvent.data)}
      // Security: prevent navigation away from mini-app domain
      onShouldStartLoadWithRequest={(req) => {
        return req.url.startsWith('https://cdn.superapp.global/mini-apps/');
      }}
      // Performance
      cacheEnabled={true}
      cacheMode="LOAD_CACHE_ELSE_NETWORK"
      // iOS-specific
      allowsInlineMediaPlayback={true}
      mediaPlaybackRequiresUserAction={false}
    />
  );
};

export default function App() {
  const [manifest, setManifest] = useState(null);

  useEffect(() => {
    // Fetch mini-app manifest on startup
    fetch('https://cdn.superapp.global/mini-apps/manifest.json')
      .then(res => res.json())
      .then(setManifest);
  }, []);

  return (
    <AuthProvider>
      <NavigationContainer>
        <Tab.Navigator>
          {/* Core tabs — always present */}
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Wallet" component={() => (
            <MiniAppScreen route={{
              params: {
                appId: 'wallet',
                bundleUrl: manifest?.apps?.wallet?.bundle_url
              }
            }} />
          )} />
          
          {/* Dynamic tabs from manifest */}
          {manifest && Object.entries(manifest.apps)
            .filter(([id, app]) => app.regions.includes(userRegion))
            .map(([id, app]) => (
              <Tab.Screen
                key={id}
                name={app.name}
                component={() => (
                  <MiniAppScreen route={{
                    params: { appId: id, bundleUrl: app.bundle_url }
                  }} />
                )}
              />
            ))
          }
        </Tab.Navigator>
      </NavigationContainer>
    </AuthProvider>
  );
}
```

---

## 4. The Bridge — JS ↔ Native API

### 4.1. Bridge Architecture

The Bridge is the secure communication channel between mini-apps (running in isolated WebViews or shadow DOM) and the host shell's native capabilities.

```
┌───────────────────────────────────────────────────────────┐
│                    MINI-APP (Isolated)                     │
│                                                           │
│  import { useBridge } from '@superapp/bridge-sdk';        │
│                                                           │
│  const bridge = useBridge();                              │
│  const location = await bridge.getLocation();             │
│  const result = await bridge.pay({ amount: 100 });        │
│                                                           │
└──────────────────────┬────────────────────────────────────┘
                       │ postMessage (structured JSON-RPC 2.0)
                       │
┌──────────────────────▼────────────────────────────────────┐
│                    BRIDGE LAYER                            │
│                                                           │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Permission Gate                                   │     │
│  │ • Check mini-app manifest permissions             │     │
│  │ • Reject unauthorized capability requests         │     │
│  │ • Rate-limit bridge calls (100/min per mini-app)  │     │
│  └──────────────────────┬───────────────────────────┘     │
│                          │                                 │
│  ┌──────────────────────▼───────────────────────────┐     │
│  │ Capability Router                                 │     │
│  │                                                   │     │
│  │ "location"  → LocationModule                     │     │
│  │ "camera"    → CameraModule                       │     │
│  │ "wallet"    → WalletCheckoutModule               │     │
│  │ "auth"      → AuthContextModule (read-only)      │     │
│  │ "storage"   → ScopedStorageModule (per-app)      │     │
│  │ "analytics" → AnalyticsModule                    │     │
│  │ "clipboard" → ClipboardModule                    │     │
│  │ "haptics"   → HapticsModule                      │     │
│  │ "share"     → NativeShareModule                  │     │
│  └──────────────────────────────────────────────────┘     │
│                                                           │
└───────────────────────────────────────────────────────────┘
                       │ Native module calls
                       ▼
┌───────────────────────────────────────────────────────────┐
│                    HOST SHELL (Native)                     │
│  • Geolocation API                                        │
│  • Camera API                                             │
│  • Payment Sheet (unified wallet checkout)                │
│  • Biometric auth (WebAuthn re-verify for payments)       │
│  • Push Notification registration                         │
└───────────────────────────────────────────────────────────┘
```

### 4.2. Bridge Protocol (JSON-RPC 2.0)

```typescript
// @superapp/bridge-sdk/types.ts

/**
 * All bridge communication uses JSON-RPC 2.0 over postMessage.
 * This ensures a standard request/response pattern with error handling.
 */

interface BridgeRequest {
  jsonrpc: "2.0";
  method: string;          // e.g., "wallet.pay", "location.getCurrent"
  params: Record<string, unknown>;
  id: string;              // Unique request ID for response correlation
}

interface BridgeResponse {
  jsonrpc: "2.0";
  result?: unknown;        // Success payload
  error?: {
    code: number;          // Standard JSON-RPC error codes
    message: string;
    data?: unknown;
  };
  id: string;              // Matches request ID
}

// Error codes
const BRIDGE_ERRORS = {
  PERMISSION_DENIED: -32001,   // Mini-app lacks required permission
  RATE_LIMITED: -32002,        // Too many bridge calls
  CAPABILITY_UNAVAILABLE: -32003, // OS capability not available
  USER_CANCELLED: -32004,     // User cancelled the action (e.g., payment sheet)
  INVALID_PARAMS: -32602,     // Standard JSON-RPC invalid params
};
```

### 4.3. Bridge SDK Implementation

```typescript
// @superapp/bridge-sdk/index.ts

export class SuperAppBridge {
  private pendingRequests = new Map<string, { resolve: Function; reject: Function; timeout: NodeJS.Timeout }>();
  private readonly REQUEST_TIMEOUT_MS = 30000;

  constructor() {
    // Listen for responses from the host shell
    window.addEventListener('message', this.handleResponse.bind(this));
  }

  /**
   * Send a bridge request and wait for the response.
   * Returns a Promise that resolves with the result or rejects with an error.
   */
  private async call<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const id = `br_${Date.now()}_${Math.random().toString(36).slice(2)}`;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new BridgeError(-32003, `Bridge call '${method}' timed out after ${this.REQUEST_TIMEOUT_MS}ms`));
      }, this.REQUEST_TIMEOUT_MS);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      const request: BridgeRequest = {
        jsonrpc: "2.0",
        method,
        params,
        id,
      };

      // Send to host shell
      if (window.ReactNativeWebView) {
        // Mobile: React Native WebView bridge
        window.ReactNativeWebView.postMessage(JSON.stringify(request));
      } else if (window.parent !== window) {
        // Web: iframe postMessage
        window.parent.postMessage(request, 'https://app.superapp.global');
      } else {
        // Web: same-origin (shadow DOM)
        window.dispatchEvent(new CustomEvent('superapp-bridge-request', { detail: request }));
      }
    });
  }

  // ──── PUBLIC API ────

  /** Get user's current location (requires "location:fine" permission) */
  async getLocation(): Promise<{ lat: number; lng: number; accuracy: number }> {
    return this.call('location.getCurrent');
  }

  /** Open the unified wallet checkout sheet */
  async pay(params: {
    amount: string;
    currency: string;
    description: string;
    merchantId?: string;
  }): Promise<{ transactionId: string; status: string }> {
    return this.call('wallet.pay', params);
  }

  /** Get the current user's profile (read-only) */
  async getUserProfile(): Promise<{
    userId: string;
    region: string;
    kycLevel: string;
    displayName: string;
  }> {
    return this.call('auth.getProfile');
  }

  /** Store data scoped to this mini-app (sandboxed) */
  async setStorage(key: string, value: string): Promise<void> {
    return this.call('storage.set', { key, value });
  }

  async getStorage(key: string): Promise<string | null> {
    return this.call('storage.get', { key });
  }

  /** Request camera access for scanning */
  async openCamera(mode: 'photo' | 'qr_scan'): Promise<{ data: string; type: string }> {
    return this.call('camera.open', { mode });
  }

  /** Trigger haptic feedback */
  async hapticFeedback(type: 'light' | 'medium' | 'heavy' | 'success' | 'error'): Promise<void> {
    return this.call('haptics.trigger', { type });
  }

  /** Open native share sheet */
  async share(params: { title: string; text?: string; url?: string }): Promise<void> {
    return this.call('share.open', params);
  }

  /** Track analytics event */
  async trackEvent(name: string, properties?: Record<string, unknown>): Promise<void> {
    return this.call('analytics.track', { name, properties });
  }

  /** Navigate to another mini-app */
  async navigateTo(appId: string, route?: string, params?: Record<string, unknown>): Promise<void> {
    return this.call('navigation.goto', { appId, route, params });
  }

  // ──── RESPONSE HANDLER ────

  private handleResponse(event: MessageEvent) {
    const response = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
    if (response.jsonrpc !== '2.0' || !response.id) return;

    const pending = this.pendingRequests.get(response.id);
    if (!pending) return;

    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id);

    if (response.error) {
      pending.reject(new BridgeError(response.error.code, response.error.message, response.error.data));
    } else {
      pending.resolve(response.result);
    }
  }
}

// Singleton export
export const bridge = new SuperAppBridge();
export const useBridge = () => bridge;
```

---

## 5. State Management

### 5.1. Global State Architecture

Global state (auth, theme, user profile) must be accessible to all mini-apps without violating isolation boundaries.

```
┌─────────────────────────────────────────────────────────┐
│                 HOST SHELL STATE                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ AuthContext (React Context)                      │   │
│  │ • accessToken (string, refreshed via interceptor)│   │
│  │ • user: { id, region, kycLevel, displayName }    │   │
│  │ • isAuthenticated (boolean)                      │   │
│  │ • login() / logout() / refresh()                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ThemeContext (React Context)                     │   │
│  │ • mode: 'dark' | 'light'                        │   │
│  │ • primaryColor, accentColor (via design tokens)  │   │
│  │ • fontFamily: 'Inter'                           │   │
│  │ • toggle()                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ RegionContext                                    │   │
│  │ • region: 'US' | 'EU' | 'INDIA'                 │   │
│  │ • locale: 'en-US' | 'en-GB' | 'hi-IN' | 'de-DE'│   │
│  │ • currency: 'USD' | 'EUR' | 'INR'               │   │
│  │ • dateFormat, numberFormat                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │                    │
        ▼            ▼                    ▼
  ┌──────────┐ ┌──────────┐       ┌──────────┐
  │Wallet MFE│ │Ride MFE  │       │Food MFE  │
  │          │ │          │       │          │
  │READ-ONLY │ │READ-ONLY │       │READ-ONLY │
  │access via│ │access via│       │access via│
  │bridge SDK│ │bridge SDK│       │bridge SDK│
  │          │ │          │       │          │
  │LOCAL     │ │LOCAL     │       │LOCAL     │
  │state is  │ │state is  │       │state is  │
  │isolated  │ │isolated  │       │isolated  │
  └──────────┘ └──────────┘       └──────────┘
```

### 5.2. State Isolation Rules

| State Type | Scope | Access Method | Memory Management |
|---|---|---|---|
| **Auth Token** | Global (shell) | Bridge SDK `auth.getProfile` | Single instance, auto-refreshed |
| **User Profile** | Global (shell) | Bridge SDK `auth.getProfile` | Cached in shell, read-only to MFEs |
| **Theme** | Global (shell) | CSS custom properties injected into WebView | No JS memory impact |
| **Mini-App Local State** | Per mini-app | React state / Redux within mini-app | Destroyed on mini-app unmount |
| **Mini-App Persistent Storage** | Per mini-app (sandboxed) | Bridge SDK `storage.get/set` | Scoped localStorage, quota: 5MB per app |
| **Cart / Order State** | Per mini-app | Internal to mini-app | Cleared on unmount unless persisted via bridge |

### 5.3. Memory Leak Prevention

```typescript
// frontend/shell/src/MiniAppContainer.tsx

class MiniAppContainer extends React.Component<MiniAppProps> {
  private webViewRef = React.createRef<WebView>();
  private memoryMonitorInterval: NodeJS.Timer | null = null;
  private crashCount = 0;

  componentDidMount() {
    // Monitor memory usage of the WebView
    this.memoryMonitorInterval = setInterval(() => {
      if (this.webViewRef.current) {
        // Check JS heap usage
        this.webViewRef.current.injectJavaScript(`
          if (performance.memory) {
            window.ReactNativeWebView.postMessage(JSON.stringify({
              jsonrpc: "2.0",
              method: "__internal.memoryReport",
              params: {
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
              },
              id: "__mem_${Date.now()}"
            }));
          }
          true;
        `);
      }
    }, 30000); // Check every 30 seconds
  }

  componentWillUnmount() {
    // CRITICAL: Clean up to prevent memory leaks
    if (this.memoryMonitorInterval) {
      clearInterval(this.memoryMonitorInterval);
    }

    // Force garbage collection hint
    if (this.webViewRef.current) {
      this.webViewRef.current.injectJavaScript(`
        // Notify mini-app to clean up
        window.dispatchEvent(new Event('superapp-unmount'));
        // Clear all intervals/timeouts
        for (let i = 0; i < 10000; i++) {
          clearInterval(i);
          clearTimeout(i);
        }
        true;
      `);
    }
  }

  handleMemoryReport(report: MemoryReport) {
    const usagePercent = report.usedJSHeapSize / report.jsHeapSizeLimit;
    
    if (usagePercent > 0.85) {
      // Memory pressure — warn the mini-app
      console.warn(`[MiniApp:${this.props.appId}] High memory: ${(usagePercent * 100).toFixed(1)}%`);
      
      // Emit bridge event to mini-app to reduce memory
      this.webViewRef.current?.injectJavaScript(`
        window.dispatchEvent(new CustomEvent('superapp-memory-pressure', {
          detail: { usage: ${usagePercent} }
        }));
        true;
      `);
    }
    
    if (usagePercent > 0.95) {
      // Critical — force reload the mini-app
      console.error(`[MiniApp:${this.props.appId}] Critical memory! Force reloading.`);
      this.webViewRef.current?.reload();
    }
  }

  handleCrash() {
    this.crashCount++;
    
    if (this.crashCount >= 3) {
      // Rollback to previous version
      const previousUrl = this.props.manifest.rollout?.rollback_url;
      if (previousUrl) {
        this.setState({ bundleUrl: previousUrl, rolledBack: true });
      }
    }
  }
}
```

---

## 6. Developer SDK & Build Tools

### 6.1. SDK Architecture

```
@superapp/mini-app-sdk
├── @superapp/bridge-sdk          # Bridge communication (see Section 4)
├── @superapp/shared-ui           # Existing: Button, Card, Input, Modal, Badge, Spinner, Toast
├── @superapp/create-mini-app     # CLI scaffold tool
├── @superapp/mini-app-cli        # Dev server, build, deploy commands
└── @superapp/testing-utils       # Test harness that mocks the bridge
```

### 6.2. CLI Scaffold Tool

```bash
# Developer creates a new mini-app
npx @superapp/create-mini-app my-ride-app

# Generated structure:
my-ride-app/
├── src/
│   ├── App.tsx                   # Root component
│   ├── index.tsx                 # Entry point with bridge initialization
│   ├── pages/
│   │   └── Home.tsx
│   └── hooks/
│       └── useSuperApp.ts        # Pre-configured bridge hooks
├── public/
│   └── index.html
├── superapp.manifest.json        # Mini-app metadata & permissions
├── vite.config.js                # Pre-configured Module Federation
├── package.json
├── tsconfig.json
└── .superapp/
    └── dev-bridge-mock.js        # Mocked bridge for local development
```

### 6.3. Mini-App Manifest (Developer-Authored)

```json
// superapp.manifest.json — authored by mini-app developer
{
  "id": "ride_hailing",
  "name": "SuperRide",
  "version": "1.0.0",
  "description": "Book rides across the city",
  "author": "Super App Internal Team",
  "icon": "./assets/icon.png",
  
  "permissions": {
    "required": [
      "location:fine",
      "wallet:pay",
      "notifications"
    ],
    "optional": [
      "contacts:read",
      "camera"
    ]
  },
  
  "regions": ["INDIA", "US"],
  "min_shell_version": "1.0.0",
  
  "entry": {
    "web": "./src/index.tsx",
    "expose": {
      "./App": "./src/App.tsx"
    }
  },
  
  "sandbox": {
    "storage_quota_mb": 10,
    "max_bridge_calls_per_minute": 200,
    "allowed_external_domains": [
      "maps.googleapis.com",
      "api.mapbox.com"
    ]
  },
  
  "review": {
    "auto_approve": false,
    "required_reviewers": ["platform-team"],
    "security_scan": true
  }
}
```

### 6.4. Deployment Pipeline for Mini-Apps

```yaml
# .github/workflows/mini-app-deploy.yml

name: Mini-App CI/CD
on:
  push:
    paths: ['mini-apps/**']

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Detect changed mini-apps
        id: changes
        run: |
          CHANGED=$(git diff --name-only HEAD~1 | grep '^mini-apps/' | cut -d'/' -f2 | sort -u)
          echo "apps=$CHANGED" >> $GITHUB_OUTPUT

      - name: Build mini-app
        run: |
          for app in ${{ steps.changes.outputs.apps }}; do
            cd mini-apps/$app
            npm ci
            npm run build
            # Generate integrity hash
            sha384sum dist/remoteEntry.js | awk '{print "sha384-" $1}' > dist/checksum.txt
          done

      - name: Security scan
        run: |
          for app in ${{ steps.changes.outputs.apps }}; do
            # Scan for known vulnerabilities
            npm audit --production
            # Scan bundle for prohibited APIs (eval, XMLHttpRequest to non-allowed domains)
            npx @superapp/security-scanner dist/
          done

      - name: Deploy to CDN (Canary 10%)
        run: |
          for app in ${{ steps.changes.outputs.apps }}; do
            VERSION=$(jq -r .version mini-apps/$app/superapp.manifest.json)
            aws s3 sync dist/ s3://superapp-miniapps/$app/v$VERSION/ \
              --cache-control "public, max-age=86400, immutable"
            
            # Update manifest with canary rollout
            npx @superapp/registry-cli update-manifest \
              --app $app \
              --version $VERSION \
              --strategy canary \
              --percentage 10
          done

      - name: Monitor canary (15 minutes)
        run: |
          sleep 900
          # Check error rates from Grafana API
          ERROR_RATE=$(curl -s "https://grafana.internal/api/ds/query" \
            --data '{"queries":[{"expr":"rate(miniapp_errors_total{app=\"$APP\"}[5m])"}]}' \
            | jq '.results[0].frames[0].data.values[1][-1]')
          
          if (( $(echo "$ERROR_RATE > 0.05" | bc -l) )); then
            echo "Error rate ${ERROR_RATE} exceeds threshold. Rolling back."
            npx @superapp/registry-cli rollback --app $APP
            exit 1
          fi

      - name: Promote to 100%
        if: success()
        run: |
          npx @superapp/registry-cli update-manifest \
            --app $APP --strategy full --percentage 100
```

---

## 7. Security Boundaries

### 7.1. Mini-App Isolation Layers

| Layer | Web | Mobile | Purpose |
|---|---|---|---|
| **Process Isolation** | iframe with `sandbox` attr | Separate WebView process | Prevent memory/CPU interference |
| **Origin Isolation** | Unique subdomain per app (`wallet.mini.superapp.global`) | WebView origin restriction | Prevent cookie/storage leakage |
| **CSP** | Strict Content-Security-Policy headers | WebView `onShouldStartLoadWithRequest` | Prevent XSS, unauthorized network calls |
| **Permission Gate** | Bridge SDK checks manifest permissions | Same | Prevent unauthorized capability access |
| **Network Isolation** | Proxy all API calls through bridge | Same | No direct backend access from mini-apps |

### 7.2. Content Security Policy for Mini-Apps

```http
Content-Security-Policy:
  default-src 'none';
  script-src 'self' https://cdn.superapp.global;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  img-src 'self' data: blob: https://cdn.superapp.global;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://api.superapp.global;
  frame-ancestors https://app.superapp.global;
  base-uri 'self';
  form-action 'none';
```

---

## 8. Performance Budgets

| Metric | Target | Measurement |
|---|---|---|
| Mini-App Bundle Size | < 500KB gzipped | CI build check |
| Mini-App First Paint | < 1.5s (from tab switch) | Web Vitals via bridge analytics |
| Bridge Call Latency (P95) | < 50ms | OTel tracing |
| Shell Cold Start | < 2s (3G connection) | Lighthouse CI |
| Memory per Mini-App | < 50MB JS heap | Memory monitor (Section 5.3) |
| Mini-App Load (OTA) | < 3s (including download + parse) | CDN metrics + client timing |

---

## 9. Open Questions

| # | Question | Owner | Deadline |
|---|---|---|---|
| 1 | Flutter instead of React Native for mobile shell? (Performance vs. ecosystem) | Mobile Lead | 2026-04-15 |
| 2 | Should mini-apps support offline mode? (Service Workers + IndexedDB via bridge) | Product | 2026-04-20 |
| 3 | Third-party mini-app submission review SLA (24h? 48h? 7 days?) | Platform | 2026-04-10 |
| 4 | Mini-app monetization model: rev-share on payments through bridge? | Business | 2026-05-01 |

---

*End of RFC-003*
