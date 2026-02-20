import Q from "react";
var O = { exports: {} }, b = {};
/**
 * @license React
 * react-jsx-runtime.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var $;
function K() {
  if ($) return b;
  $ = 1;
  var l = Symbol.for("react.transitional.element"), f = Symbol.for("react.fragment");
  function u(c, o, s) {
    var i = null;
    if (s !== void 0 && (i = "" + s), o.key !== void 0 && (i = "" + o.key), "key" in o) {
      s = {};
      for (var m in o)
        m !== "key" && (s[m] = o[m]);
    } else s = o;
    return o = s.ref, {
      $$typeof: l,
      type: c,
      key: i,
      ref: o !== void 0 ? o : null,
      props: s
    };
  }
  return b.Fragment = f, b.jsx = u, b.jsxs = u, b;
}
var _ = {};
/**
 * @license React
 * react-jsx-runtime.development.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var I;
function ee() {
  return I || (I = 1, process.env.NODE_ENV !== "production" && function() {
    function l(e) {
      if (e == null) return null;
      if (typeof e == "function")
        return e.$$typeof === B ? null : e.displayName || e.name || null;
      if (typeof e == "string") return e;
      switch (e) {
        case p:
          return "Fragment";
        case W:
          return "Profiler";
        case M:
          return "StrictMode";
        case q:
          return "Suspense";
        case G:
          return "SuspenseList";
        case X:
          return "Activity";
      }
      if (typeof e == "object")
        switch (typeof e.tag == "number" && console.error(
          "Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."
        ), e.$$typeof) {
          case L:
            return "Portal";
          case V:
            return e.displayName || "Context";
          case U:
            return (e._context.displayName || "Context") + ".Consumer";
          case z:
            var r = e.render;
            return e = e.displayName, e || (e = r.displayName || r.name || "", e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef"), e;
          case J:
            return r = e.displayName || null, r !== null ? r : l(e.type) || "Memo";
          case R:
            r = e._payload, e = e._init;
            try {
              return l(e(r));
            } catch {
            }
        }
      return null;
    }
    function f(e) {
      return "" + e;
    }
    function u(e) {
      try {
        f(e);
        var r = !1;
      } catch {
        r = !0;
      }
      if (r) {
        r = console;
        var t = r.error, n = typeof Symbol == "function" && Symbol.toStringTag && e[Symbol.toStringTag] || e.constructor.name || "Object";
        return t.call(
          r,
          "The provided key is an unsupported type %s. This value must be coerced to a string before using it here.",
          n
        ), f(e);
      }
    }
    function c(e) {
      if (e === p) return "<>";
      if (typeof e == "object" && e !== null && e.$$typeof === R)
        return "<...>";
      try {
        var r = l(e);
        return r ? "<" + r + ">" : "<...>";
      } catch {
        return "<...>";
      }
    }
    function o() {
      var e = T.A;
      return e === null ? null : e.getOwner();
    }
    function s() {
      return Error("react-stack-top-frame");
    }
    function i(e) {
      if (x.call(e, "key")) {
        var r = Object.getOwnPropertyDescriptor(e, "key").get;
        if (r && r.isReactWarning) return !1;
      }
      return e.key !== void 0;
    }
    function m(e, r) {
      function t() {
        h || (h = !0, console.error(
          "%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://react.dev/link/special-props)",
          r
        ));
      }
      t.isReactWarning = !0, Object.defineProperty(e, "key", {
        get: t,
        configurable: !0
      });
    }
    function F() {
      var e = l(this.type);
      return j[e] || (j[e] = !0, console.error(
        "Accessing element.ref was removed in React 19. ref is now a regular prop. It will be removed from the JSX Element type in a future release."
      )), e = this.props.ref, e !== void 0 ? e : null;
    }
    function D(e, r, t, n, v, k) {
      var a = t.ref;
      return e = {
        $$typeof: P,
        type: e,
        key: r,
        props: t,
        _owner: n
      }, (a !== void 0 ? a : null) !== null ? Object.defineProperty(e, "ref", {
        enumerable: !1,
        get: F
      }) : Object.defineProperty(e, "ref", { enumerable: !1, value: null }), e._store = {}, Object.defineProperty(e._store, "validated", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: 0
      }), Object.defineProperty(e, "_debugInfo", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: null
      }), Object.defineProperty(e, "_debugStack", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: v
      }), Object.defineProperty(e, "_debugTask", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: k
      }), Object.freeze && (Object.freeze(e.props), Object.freeze(e)), e;
    }
    function A(e, r, t, n, v, k) {
      var a = r.children;
      if (a !== void 0)
        if (n)
          if (H(a)) {
            for (n = 0; n < a.length; n++)
              S(a[n]);
            Object.freeze && Object.freeze(a);
          } else
            console.error(
              "React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead."
            );
        else S(a);
      if (x.call(r, "key")) {
        a = l(e);
        var d = Object.keys(r).filter(function(Z) {
          return Z !== "key";
        });
        n = 0 < d.length ? "{key: someKey, " + d.join(": ..., ") + ": ...}" : "{key: someKey}", Y[a + n] || (d = 0 < d.length ? "{" + d.join(": ..., ") + ": ...}" : "{}", console.error(
          `A props object containing a "key" prop is being spread into JSX:
  let props = %s;
  <%s {...props} />
React keys must be passed directly to JSX without using spread:
  let props = %s;
  <%s key={someKey} {...props} />`,
          n,
          a,
          d,
          a
        ), Y[a + n] = !0);
      }
      if (a = null, t !== void 0 && (u(t), a = "" + t), i(r) && (u(r.key), a = "" + r.key), "key" in r) {
        t = {};
        for (var y in r)
          y !== "key" && (t[y] = r[y]);
      } else t = r;
      return a && m(
        t,
        typeof e == "function" ? e.displayName || e.name || "Unknown" : e
      ), D(
        e,
        a,
        t,
        o(),
        v,
        k
      );
    }
    function S(e) {
      w(e) ? e._store && (e._store.validated = 1) : typeof e == "object" && e !== null && e.$$typeof === R && (e._payload.status === "fulfilled" ? w(e._payload.value) && e._payload.value._store && (e._payload.value._store.validated = 1) : e._store && (e._store.validated = 1));
    }
    function w(e) {
      return typeof e == "object" && e !== null && e.$$typeof === P;
    }
    var E = Q, P = Symbol.for("react.transitional.element"), L = Symbol.for("react.portal"), p = Symbol.for("react.fragment"), M = Symbol.for("react.strict_mode"), W = Symbol.for("react.profiler"), U = Symbol.for("react.consumer"), V = Symbol.for("react.context"), z = Symbol.for("react.forward_ref"), q = Symbol.for("react.suspense"), G = Symbol.for("react.suspense_list"), J = Symbol.for("react.memo"), R = Symbol.for("react.lazy"), X = Symbol.for("react.activity"), B = Symbol.for("react.client.reference"), T = E.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, x = Object.prototype.hasOwnProperty, H = Array.isArray, g = console.createTask ? console.createTask : function() {
      return null;
    };
    E = {
      react_stack_bottom_frame: function(e) {
        return e();
      }
    };
    var h, j = {}, N = E.react_stack_bottom_frame.bind(
      E,
      s
    )(), C = g(c(s)), Y = {};
    _.Fragment = p, _.jsx = function(e, r, t) {
      var n = 1e4 > T.recentlyCreatedOwnerStacks++;
      return A(
        e,
        r,
        t,
        !1,
        n ? Error("react-stack-top-frame") : N,
        n ? g(c(e)) : C
      );
    }, _.jsxs = function(e, r, t) {
      var n = 1e4 > T.recentlyCreatedOwnerStacks++;
      return A(
        e,
        r,
        t,
        !0,
        n ? Error("react-stack-top-frame") : N,
        n ? g(c(e)) : C
      );
    };
  }()), _;
}
process.env.NODE_ENV === "production" ? O.exports = K() : O.exports = ee();
var re = O.exports;
const ne = ({ children: l, onClick: f, variant: u = "primary", className: c = "", ...o }) => {
  const s = "px-4 py-2 rounded font-semibold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed", i = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500",
    danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
  };
  return /* @__PURE__ */ re.jsx(
    "button",
    {
      onClick: f,
      className: `${s} ${i[u]} ${c}`,
      ...o,
      children: l
    }
  );
};
export {
  ne as Button
};
