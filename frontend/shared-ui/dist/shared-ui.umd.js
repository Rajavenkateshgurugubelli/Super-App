(function(b,g){typeof exports=="object"&&typeof module<"u"?g(exports,require("react")):typeof define=="function"&&define.amd?define(["exports","react"],g):(b=typeof globalThis<"u"?globalThis:b||self,g(b.SharedUI={},b.React))})(this,function(b,g){"use strict";var N={exports:{}},h={};/**
 * @license React
 * react-jsx-runtime.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var P;function K(){if(P)return h;P=1;var t=Symbol.for("react.transitional.element"),r=Symbol.for("react.fragment");function i(l,s,a){var u=null;if(a!==void 0&&(u=""+a),s.key!==void 0&&(u=""+s.key),"key"in s){a={};for(var c in s)c!=="key"&&(a[c]=s[c])}else a=s;return s=a.ref,{$$typeof:t,type:l,key:u,ref:s!==void 0?s:null,props:a}}return h.Fragment=r,h.jsx=i,h.jsxs=i,h}var y={};/**
 * @license React
 * react-jsx-runtime.development.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var O;function ee(){return O||(O=1,process.env.NODE_ENV!=="production"&&function(){function t(e){if(e==null)return null;if(typeof e=="function")return e.$$typeof===Ae?null:e.displayName||e.name||null;if(typeof e=="string")return e;switch(e){case j:return"Fragment";case we:return"Profiler";case _e:return"StrictMode";case je:return"Suspense";case Re:return"SuspenseList";case Ce:return"Activity"}if(typeof e=="object")switch(typeof e.tag=="number"&&console.error("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."),e.$$typeof){case ve:return"Portal";case Ee:return e.displayName||"Context";case ke:return(e._context.displayName||"Context")+".Consumer";case Ne:var o=e.render;return e=e.displayName,e||(e=o.displayName||o.name||"",e=e!==""?"ForwardRef("+e+")":"ForwardRef"),e;case Te:return o=e.displayName||null,o!==null?o:t(e.type)||"Memo";case R:o=e._payload,e=e._init;try{return t(e(o))}catch{}}return null}function r(e){return""+e}function i(e){try{r(e);var o=!1}catch{o=!0}if(o){o=console;var d=o.error,f=typeof Symbol=="function"&&Symbol.toStringTag&&e[Symbol.toStringTag]||e.constructor.name||"Object";return d.call(o,"The provided key is an unsupported type %s. This value must be coerced to a string before using it here.",f),r(e)}}function l(e){if(e===j)return"<>";if(typeof e=="object"&&e!==null&&e.$$typeof===R)return"<...>";try{var o=t(e);return o?"<"+o+">":"<...>"}catch{return"<...>"}}function s(){var e=T.A;return e===null?null:e.getOwner()}function a(){return Error("react-stack-top-frame")}function u(e){if(G.call(e,"key")){var o=Object.getOwnPropertyDescriptor(e,"key").get;if(o&&o.isReactWarning)return!1}return e.key!==void 0}function c(e,o){function d(){J||(J=!0,console.error("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://react.dev/link/special-props)",o))}d.isReactWarning=!0,Object.defineProperty(e,"key",{get:d,configurable:!0})}function v(){var e=t(this.type);return H[e]||(H[e]=!0,console.error("Accessing element.ref was removed in React 19. ref is now a regular prop. It will be removed from the JSX Element type in a future release.")),e=this.props.ref,e!==void 0?e:null}function _(e,o,d,f,E,A){var m=d.ref;return e={$$typeof:X,type:e,key:o,props:d,_owner:f},(m!==void 0?m:null)!==null?Object.defineProperty(e,"ref",{enumerable:!1,get:v}):Object.defineProperty(e,"ref",{enumerable:!1,value:null}),e._store={},Object.defineProperty(e._store,"validated",{configurable:!1,enumerable:!1,writable:!0,value:0}),Object.defineProperty(e,"_debugInfo",{configurable:!1,enumerable:!1,writable:!0,value:null}),Object.defineProperty(e,"_debugStack",{configurable:!1,enumerable:!1,writable:!0,value:E}),Object.defineProperty(e,"_debugTask",{configurable:!1,enumerable:!1,writable:!0,value:A}),Object.freeze&&(Object.freeze(e.props),Object.freeze(e)),e}function w(e,o,d,f,E,A){var m=o.children;if(m!==void 0)if(f)if(Se(m)){for(f=0;f<m.length;f++)B(m[f]);Object.freeze&&Object.freeze(m)}else console.error("React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead.");else B(m);if(G.call(o,"key")){m=t(e);var p=Object.keys(o).filter(function(Pe){return Pe!=="key"});f=0<p.length?"{key: someKey, "+p.join(": ..., ")+": ...}":"{key: someKey}",q[m+f]||(p=0<p.length?"{"+p.join(": ..., ")+": ...}":"{}",console.error(`A props object containing a "key" prop is being spread into JSX:
  let props = %s;
  <%s {...props} />
React keys must be passed directly to JSX without using spread:
  let props = %s;
  <%s key={someKey} {...props} />`,f,m,p,m),q[m+f]=!0)}if(m=null,d!==void 0&&(i(d),m=""+d),u(o)&&(i(o.key),m=""+o.key),"key"in o){d={};for(var S in o)S!=="key"&&(d[S]=o[S])}else d=o;return m&&c(d,typeof e=="function"?e.displayName||e.name||"Unknown":e),_(e,m,d,s(),E,A)}function B(e){V(e)?e._store&&(e._store.validated=1):typeof e=="object"&&e!==null&&e.$$typeof===R&&(e._payload.status==="fulfilled"?V(e._payload.value)&&e._payload.value._store&&(e._payload.value._store.validated=1):e._store&&(e._store.validated=1))}function V(e){return typeof e=="object"&&e!==null&&e.$$typeof===X}var k=g,X=Symbol.for("react.transitional.element"),ve=Symbol.for("react.portal"),j=Symbol.for("react.fragment"),_e=Symbol.for("react.strict_mode"),we=Symbol.for("react.profiler"),ke=Symbol.for("react.consumer"),Ee=Symbol.for("react.context"),Ne=Symbol.for("react.forward_ref"),je=Symbol.for("react.suspense"),Re=Symbol.for("react.suspense_list"),Te=Symbol.for("react.memo"),R=Symbol.for("react.lazy"),Ce=Symbol.for("react.activity"),Ae=Symbol.for("react.client.reference"),T=k.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE,G=Object.prototype.hasOwnProperty,Se=Array.isArray,C=console.createTask?console.createTask:function(){return null};k={react_stack_bottom_frame:function(e){return e()}};var J,H={},Z=k.react_stack_bottom_frame.bind(k,a)(),Q=C(l(a)),q={};y.Fragment=j,y.jsx=function(e,o,d){var f=1e4>T.recentlyCreatedOwnerStacks++;return w(e,o,d,!1,f?Error("react-stack-top-frame"):Z,f?C(l(e)):Q)},y.jsxs=function(e,o,d){var f=1e4>T.recentlyCreatedOwnerStacks++;return w(e,o,d,!0,f?Error("react-stack-top-frame"):Z,f?C(l(e)):Q)}}()),y}process.env.NODE_ENV==="production"?N.exports=K():N.exports=ee();var n=N.exports;const re=({children:t,onClick:r,variant:i="primary",className:l="",...s})=>{const a="px-4 py-2 rounded font-semibold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed",u={primary:"bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",secondary:"bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500",danger:"bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"};return n.jsx("button",{onClick:r,className:`${a} ${u[i]} ${l}`,...s,children:t})},te=({children:t,className:r=""})=>n.jsx("div",{className:`bg-gray-800/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-xl overflow-hidden ${r}`,children:t}),ne=({children:t,className:r=""})=>n.jsx("div",{className:`px-6 py-5 border-b border-white/5 ${r}`,children:t}),oe=({children:t,className:r=""})=>n.jsx("h3",{className:`text-lg font-medium text-white ${r}`,children:t}),ae=({children:t,className:r=""})=>n.jsx("div",{className:`p-6 ${r}`,children:t});/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const $=(...t)=>t.filter((r,i,l)=>!!r&&r.trim()!==""&&l.indexOf(r)===i).join(" ").trim();/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const se=t=>t.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase();/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ie=t=>t.replace(/^([A-Z])|[\s-_]+(\w)/g,(r,i,l)=>l?l.toUpperCase():i.toLowerCase());/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const I=t=>{const r=ie(t);return r.charAt(0).toUpperCase()+r.slice(1)};/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */var le={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:2,strokeLinecap:"round",strokeLinejoin:"round"};/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ce=t=>{for(const r in t)if(r.startsWith("aria-")||r==="role"||r==="title")return!0;return!1};/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const de=g.forwardRef(({color:t="currentColor",size:r=24,strokeWidth:i=2,absoluteStrokeWidth:l,className:s="",children:a,iconNode:u,...c},v)=>g.createElement("svg",{ref:v,...le,width:r,height:r,stroke:t,strokeWidth:l?Number(i)*24/Number(r):i,className:$("lucide",s),...!a&&!ce(c)&&{"aria-hidden":"true"},...c},[...u.map(([_,w])=>g.createElement(_,w)),...Array.isArray(a)?a:[a]]));/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const x=(t,r)=>{const i=g.forwardRef(({className:l,...s},a)=>g.createElement(de,{ref:a,iconNode:r,className:$(`lucide-${se(I(t))}`,`lucide-${t}`,l),...s}));return i.displayName=I(t),i};/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ue=x("circle-alert",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["line",{x1:"12",x2:"12",y1:"8",y2:"12",key:"1pkeuh"}],["line",{x1:"12",x2:"12.01",y1:"16",y2:"16",key:"4dfq90"}]]);/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const fe=x("circle-check-big",[["path",{d:"M21.801 10A10 10 0 1 1 17 3.335",key:"yps3ct"}],["path",{d:"m9 11 3 3L22 4",key:"1pflzl"}]]);/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const me=x("circle-x",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"m15 9-6 6",key:"1uzhvr"}],["path",{d:"m9 9 6 6",key:"z0biqf"}]]);/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const be=x("info",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"M12 16v-4",key:"1dtifu"}],["path",{d:"M12 8h.01",key:"e9boi3"}]]);/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ge=x("triangle-alert",[["path",{d:"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3",key:"wmoenq"}],["path",{d:"M12 9v4",key:"juzpu7"}],["path",{d:"M12 17h.01",key:"p32p05"}]]);/**
 * @license lucide-react v0.577.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M=x("x",[["path",{d:"M18 6 6 18",key:"1bl5f8"}],["path",{d:"m6 6 12 12",key:"d8bk6v"}]]),L=g.forwardRef(({label:t,error:r,icon:i,className:l="",id:s,...a},u)=>{const c=s||(t==null?void 0:t.toLowerCase().replace(/\s+/g,"-"));return n.jsxs("div",{className:`flex flex-col gap-1.5 ${l}`,children:[t&&n.jsx("label",{htmlFor:c,className:"text-sm font-medium text-gray-300",children:t}),n.jsxs("div",{className:"relative",children:[i&&n.jsx("div",{className:"absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none",children:n.jsx(i,{className:"h-5 w-5 text-gray-400"})}),n.jsx("input",{ref:u,id:c,className:`
            w-full bg-gray-900/50 border rounded-xl px-4 py-2.5 
            text-white placeholder-gray-500 focus:outline-none focus:ring-2 
            transition-all duration-200
            ${i?"pl-10":""}
            ${r?"border-red-500 focus:ring-red-500/20":"border-white/10 focus:border-indigo-500 focus:ring-indigo-500/20"}
          `,...a}),r&&n.jsx("div",{className:"absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none",children:n.jsx(ue,{className:"h-5 w-5 text-red-500"})})]}),r&&n.jsx("p",{className:"text-sm text-red-500 mt-1 animate-in fade-in slide-in-from-top-1",children:r})]})});L.displayName="Input";const xe=({isOpen:t,onClose:r,title:i,children:l})=>{const s=g.useRef(null);return g.useEffect(()=>{const a=u=>{u.key==="Escape"&&r()};return t&&(document.addEventListener("keydown",a),document.body.style.overflow="hidden"),()=>{document.removeEventListener("keydown",a),document.body.style.overflow="unset"}},[t,r]),t?n.jsxs("div",{className:"fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6",children:[n.jsx("div",{ref:s,className:"absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity",onClick:a=>{a.target===s.current&&r()},"aria-hidden":"true"}),n.jsxs("div",{className:`relative bg-gray-900 border border-white/10 rounded-2xl shadow-2xl w-full max-w-md \r
                   transform transition-all animate-in zoom-in-95 duration-200 fade-in flex flex-col max-h-[90vh]`,role:"dialog","aria-modal":"true",children:[n.jsxs("div",{className:"flex items-center justify-between px-6 py-4 border-b border-white/10",children:[n.jsx("h3",{className:"text-lg font-semibold text-white",children:i}),n.jsx("button",{onClick:r,className:"text-gray-400 hover:text-white transition-colors p-1 rounded-full hover:bg-white/5",children:n.jsx(M,{className:"w-5 h-5"})})]}),n.jsx("div",{className:"p-6 overflow-y-auto",children:l})]})]}):null},Y={success:"bg-emerald-500/15 text-emerald-400 ring-emerald-500/25",warning:"bg-amber-500/15 text-amber-400 ring-amber-500/25",error:"bg-red-500/15 text-red-400 ring-red-500/25",info:"bg-indigo-500/15 text-indigo-400 ring-indigo-500/25",neutral:"bg-gray-500/15 text-gray-300 ring-gray-500/25",USD:"bg-emerald-500/15 text-emerald-300 ring-emerald-500/25",EUR:"bg-blue-500/15 text-blue-300 ring-blue-500/25",INR:"bg-orange-500/15 text-orange-300 ring-orange-500/25"},U={sm:"px-1.5 py-0.5 text-xs",md:"px-2.5 py-1 text-xs",lg:"px-3 py-1.5 text-sm"},D={success:"bg-emerald-400",warning:"bg-amber-400",error:"bg-red-400",info:"bg-indigo-400",neutral:"bg-gray-400",USD:"bg-emerald-400",EUR:"bg-blue-400",INR:"bg-orange-400"},pe=({children:t,variant:r="neutral",size:i="md",dot:l=!1,className:s=""})=>{const a=Y[r]??Y.neutral,u=U[i]??U.md,c=D[r]??D.neutral;return n.jsxs("span",{className:`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ring-1 ring-inset whitespace-nowrap
        ${a} ${u} ${s}
      `,children:[l&&n.jsxs("span",{className:"relative flex h-2 w-2 shrink-0",children:[n.jsx("span",{className:`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${c}`}),n.jsx("span",{className:`relative inline-flex h-2 w-2 rounded-full ${c}`})]}),t]})},z={sm:{outer:"h-4 w-4",inner:"h-2.5 w-2.5",border:"border-2"},md:{outer:"h-8 w-8",inner:"h-5 w-5",border:"border-2"},lg:{outer:"h-12 w-12",inner:"h-7 w-7",border:"border-[3px]"}},F={indigo:"border-indigo-500",violet:"border-violet-500",cyan:"border-cyan-500",white:"border-white"},he=({size:t="md",color:r="indigo",label:i="Loading…",className:l=""})=>{const s=z[t]??z.md,a=F[r]??F.indigo;return n.jsxs("span",{role:"status","aria-label":i,className:`inline-flex items-center justify-center ${s.outer} ${l}`,children:[n.jsx("span",{className:`
          ${s.inner} rounded-full border-transparent ${s.border} ${a}
          animate-spin border-t-current
        `,style:{borderTopColor:"currentColor"}}),n.jsx("span",{className:"sr-only",children:i})]})},W={success:{icon:fe,bar:"bg-emerald-500",bg:"bg-gray-900/95 border-emerald-500/30",icon_color:"text-emerald-400",title_color:"text-emerald-300"},error:{icon:me,bar:"bg-red-500",bg:"bg-gray-900/95 border-red-500/30",icon_color:"text-red-400",title_color:"text-red-300"},warning:{icon:ge,bar:"bg-amber-500",bg:"bg-gray-900/95 border-amber-500/30",icon_color:"text-amber-400",title_color:"text-amber-300"},info:{icon:be,bar:"bg-indigo-500",bg:"bg-gray-900/95 border-indigo-500/30",icon_color:"text-indigo-400",title_color:"text-indigo-300"}},ye=({isOpen:t,onClose:r,variant:i="info",title:l,message:s,duration:a=4e3})=>{const u=g.useCallback(()=>r==null?void 0:r(),[r]);if(g.useEffect(()=>{if(!t||a===0)return;const _=setTimeout(u,a);return()=>clearTimeout(_)},[t,a,u]),!t)return null;const c=W[i]??W.info,v=c.icon;return n.jsxs("div",{role:"alert","aria-live":"assertive",className:"fixed bottom-6 right-6 z-[9999] flex min-w-[300px] max-w-sm flex-col overflow-hidden rounded-xl border shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom-4 fade-in duration-300",style:{willChange:"transform"},children:[n.jsx("div",{className:`h-1 w-full ${c.bar}`}),n.jsxs("div",{className:`flex items-start gap-3 p-4 ${c.bg}`,children:[n.jsx(v,{className:`mt-0.5 h-5 w-5 shrink-0 ${c.icon_color}`}),n.jsxs("div",{className:"flex-1 min-w-0",children:[l&&n.jsx("p",{className:`text-sm font-semibold leading-5 ${c.title_color}`,children:l}),s&&n.jsx("p",{className:"mt-0.5 text-sm text-gray-400 leading-5",children:s})]}),n.jsx("button",{onClick:u,"aria-label":"Dismiss",className:"shrink-0 text-gray-500 hover:text-gray-300 transition-colors p-0.5 rounded",children:n.jsx(M,{className:"h-4 w-4"})})]}),a>0&&n.jsx("div",{className:`h-0.5 w-full ${c.bar} opacity-40`,children:n.jsx("div",{className:`h-full ${c.bar}`,style:{animation:`shrink ${a}ms linear forwards`}})}),n.jsx("style",{children:`
        @keyframes shrink {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `})]})};b.Badge=pe,b.Button=re,b.Card=te,b.CardContent=ae,b.CardHeader=ne,b.CardTitle=oe,b.Input=L,b.Modal=xe,b.Spinner=he,b.Toast=ye,Object.defineProperty(b,Symbol.toStringTag,{value:"Module"})});
