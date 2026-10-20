var Rr=Object.create;var jn=Object.defineProperty;var Hr=Object.getOwnPropertyDescriptor;var Dr=Object.getOwnPropertyNames;var Fr=Object.getPrototypeOf,Wr=Object.prototype.hasOwnProperty;var qr=(l,s)=>()=>(s||l((s={exports:{}}).exports,s),s.exports);var Ur=(l,s,a,d)=>{if(s&&typeof s=="object"||typeof s=="function")for(let p of Dr(s))!Wr.call(l,p)&&p!==a&&jn(l,p,{get:()=>s[p],enumerable:!(d=Hr(s,p))||d.enumerable});return l};var Kn=(l,s,a)=>(a=l!=null?Rr(Fr(l)):{},Ur(s||!l||!l.__esModule?jn(a,"default",{value:l,enumerable:!0}):a,l));var zi=qr((Ve,Yn)=>{(function(l,s){typeof Ve=="object"&&typeof Yn<"u"?s(Ve):typeof define=="function"&&define.amd?define(["exports"],s):(l=typeof globalThis<"u"?globalThis:l||self,s(l.leaflet={}))})(Ve,(function(l){"use strict";var s="1.9.4";function a(t){var e,i,n,o;for(i=1,n=arguments.length;i<n;i++){o=arguments[i];for(e in o)t[e]=o[e]}return t}var d=Object.create||(function(){function t(){}return function(e){return t.prototype=e,new t}})();function p(t,e){var i=Array.prototype.slice;if(t.bind)return t.bind.apply(t,i.call(arguments,1));var n=i.call(arguments,2);return function(){return t.apply(e,n.length?n.concat(i.call(arguments)):arguments)}}var h=0;function f(t){return"_leaflet_id"in t||(t._leaflet_id=++h),t._leaflet_id}function g(t,e,i){var n,o,r,c;return c=function(){n=!1,o&&(r.apply(i,o),o=!1)},r=function(){n?o=arguments:(t.apply(i,arguments),setTimeout(c,e),n=!0)},r}function P(t,e,i){var n=e[1],o=e[0],r=n-o;return t===n&&i?t:((t-o)%r+r)%r+o}function _(){return!1}function C(t,e){if(e===!1)return t;var i=Math.pow(10,e===void 0?6:e);return Math.round(t*i)/i}function j(t){return t.trim?t.trim():t.replace(/^\s+|\s+$/g,"")}function Z(t){return j(t).split(/\s+/)}function w(t,e){Object.prototype.hasOwnProperty.call(t,"options")||(t.options=t.options?d(t.options):{});for(var i in e)t.options[i]=e[i];return t.options}function z(t,e,i){var n=[];for(var o in t)n.push(encodeURIComponent(i?o.toUpperCase():o)+"="+encodeURIComponent(t[o]));return(!e||e.indexOf("?")===-1?"?":"&")+n.join("&")}var q=/\{ *([\w_ -]+) *\}/g;function D(t,e){return t.replace(q,function(i,n){var o=e[n];if(o===void 0)throw new Error("No value provided for variable "+i);return typeof o=="function"&&(o=o(e)),o})}var A=Array.isArray||function(t){return Object.prototype.toString.call(t)==="[object Array]"};function X(t,e){for(var i=0;i<t.length;i++)if(t[i]===e)return i;return-1}var F="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=";function yt(t){return window["webkit"+t]||window["moz"+t]||window["ms"+t]}var ct=0;function b(t){var e=+new Date,i=Math.max(0,16-(e-ct));return ct=e+i,window.setTimeout(t,i)}var H=window.requestAnimationFrame||yt("RequestAnimationFrame")||b,T=window.cancelAnimationFrame||yt("CancelAnimationFrame")||yt("CancelRequestAnimationFrame")||function(t){window.clearTimeout(t)};function M(t,e,i){if(i&&H===b)t.call(e);else return H.call(window,p(t,e))}function y(t){t&&T.call(window,t)}var J={__proto__:null,extend:a,create:d,bind:p,get lastId(){return h},stamp:f,throttle:g,wrapNum:P,falseFn:_,formatNum:C,trim:j,splitWords:Z,setOptions:w,getParamString:z,template:D,isArray:A,indexOf:X,emptyImageUrl:F,requestFn:H,cancelFn:T,requestAnimFrame:M,cancelAnimFrame:y};function Q(){}Q.extend=function(t){var e=function(){w(this),this.initialize&&this.initialize.apply(this,arguments),this.callInitHooks()},i=e.__super__=this.prototype,n=d(i);n.constructor=e,e.prototype=n;for(var o in this)Object.prototype.hasOwnProperty.call(this,o)&&o!=="prototype"&&o!=="__super__"&&(e[o]=this[o]);return t.statics&&a(e,t.statics),t.includes&&(Ut(t.includes),a.apply(null,[n].concat(t.includes))),a(n,t),delete n.statics,delete n.includes,n.options&&(n.options=i.options?d(i.options):{},a(n.options,t.options)),n._initHooks=[],n.callInitHooks=function(){if(!this._initHooksCalled){i.callInitHooks&&i.callInitHooks.call(this),this._initHooksCalled=!0;for(var r=0,c=n._initHooks.length;r<c;r++)n._initHooks[r].call(this)}},e},Q.include=function(t){var e=this.prototype.options;return a(this.prototype,t),t.options&&(this.prototype.options=e,this.mergeOptions(t.options)),this},Q.mergeOptions=function(t){return a(this.prototype.options,t),this},Q.addInitHook=function(t){var e=Array.prototype.slice.call(arguments,1),i=typeof t=="function"?t:function(){this[t].apply(this,e)};return this.prototype._initHooks=this.prototype._initHooks||[],this.prototype._initHooks.push(i),this};function Ut(t){if(!(typeof L>"u"||!L||!L.Mixin)){t=A(t)?t:[t];for(var e=0;e<t.length;e++)t[e]===L.Mixin.Events&&console.warn("Deprecated include of L.Mixin.Events: this property will be removed in future releases, please inherit from L.Evented instead.",new Error().stack)}}var lt={on:function(t,e,i){if(typeof t=="object")for(var n in t)this._on(n,t[n],e);else{t=Z(t);for(var o=0,r=t.length;o<r;o++)this._on(t[o],e,i)}return this},off:function(t,e,i){if(!arguments.length)delete this._events;else if(typeof t=="object")for(var n in t)this._off(n,t[n],e);else{t=Z(t);for(var o=arguments.length===1,r=0,c=t.length;r<c;r++)o?this._off(t[r]):this._off(t[r],e,i)}return this},_on:function(t,e,i,n){if(typeof e!="function"){console.warn("wrong listener type: "+typeof e);return}if(this._listens(t,e,i)===!1){i===this&&(i=void 0);var o={fn:e,ctx:i};n&&(o.once=!0),this._events=this._events||{},this._events[t]=this._events[t]||[],this._events[t].push(o)}},_off:function(t,e,i){var n,o,r;if(this._events&&(n=this._events[t],!!n)){if(arguments.length===1){if(this._firingCount)for(o=0,r=n.length;o<r;o++)n[o].fn=_;delete this._events[t];return}if(typeof e!="function"){console.warn("wrong listener type: "+typeof e);return}var c=this._listens(t,e,i);if(c!==!1){var u=n[c];this._firingCount&&(u.fn=_,this._events[t]=n=n.slice()),n.splice(c,1)}}},fire:function(t,e,i){if(!this.listens(t,i))return this;var n=a({},e,{type:t,target:this,sourceTarget:e&&e.sourceTarget||this});if(this._events){var o=this._events[t];if(o){this._firingCount=this._firingCount+1||1;for(var r=0,c=o.length;r<c;r++){var u=o[r],m=u.fn;u.once&&this.off(t,m,u.ctx),m.call(u.ctx||this,n)}this._firingCount--}}return i&&this._propagateEvent(n),this},listens:function(t,e,i,n){typeof t!="string"&&console.warn('"string" type argument expected');var o=e;typeof e!="function"&&(n=!!e,o=void 0,i=void 0);var r=this._events&&this._events[t];if(r&&r.length&&this._listens(t,o,i)!==!1)return!0;if(n){for(var c in this._eventParents)if(this._eventParents[c].listens(t,e,i,n))return!0}return!1},_listens:function(t,e,i){if(!this._events)return!1;var n=this._events[t]||[];if(!e)return!!n.length;i===this&&(i=void 0);for(var o=0,r=n.length;o<r;o++)if(n[o].fn===e&&n[o].ctx===i)return o;return!1},once:function(t,e,i){if(typeof t=="object")for(var n in t)this._on(n,t[n],e,!0);else{t=Z(t);for(var o=0,r=t.length;o<r;o++)this._on(t[o],e,i,!0)}return this},addEventParent:function(t){return this._eventParents=this._eventParents||{},this._eventParents[f(t)]=t,this},removeEventParent:function(t){return this._eventParents&&delete this._eventParents[f(t)],this},_propagateEvent:function(t){for(var e in this._eventParents)this._eventParents[e].fire(t.type,a({layer:t.target,propagatedFrom:t.target},t),!0)}};lt.addEventListener=lt.on,lt.removeEventListener=lt.clearAllEventListeners=lt.off,lt.addOneTimeEventListener=lt.once,lt.fireEvent=lt.fire,lt.hasEventListeners=lt.listens;var wt=Q.extend(lt);function N(t,e,i){this.x=i?Math.round(t):t,this.y=i?Math.round(e):e}var Me=Math.trunc||function(t){return t>0?Math.floor(t):Math.ceil(t)};N.prototype={clone:function(){return new N(this.x,this.y)},add:function(t){return this.clone()._add(I(t))},_add:function(t){return this.x+=t.x,this.y+=t.y,this},subtract:function(t){return this.clone()._subtract(I(t))},_subtract:function(t){return this.x-=t.x,this.y-=t.y,this},divideBy:function(t){return this.clone()._divideBy(t)},_divideBy:function(t){return this.x/=t,this.y/=t,this},multiplyBy:function(t){return this.clone()._multiplyBy(t)},_multiplyBy:function(t){return this.x*=t,this.y*=t,this},scaleBy:function(t){return new N(this.x*t.x,this.y*t.y)},unscaleBy:function(t){return new N(this.x/t.x,this.y/t.y)},round:function(){return this.clone()._round()},_round:function(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this},floor:function(){return this.clone()._floor()},_floor:function(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this},ceil:function(){return this.clone()._ceil()},_ceil:function(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this},trunc:function(){return this.clone()._trunc()},_trunc:function(){return this.x=Me(this.x),this.y=Me(this.y),this},distanceTo:function(t){t=I(t);var e=t.x-this.x,i=t.y-this.y;return Math.sqrt(e*e+i*i)},equals:function(t){return t=I(t),t.x===this.x&&t.y===this.y},contains:function(t){return t=I(t),Math.abs(t.x)<=Math.abs(this.x)&&Math.abs(t.y)<=Math.abs(this.y)},toString:function(){return"Point("+C(this.x)+", "+C(this.y)+")"}};function I(t,e,i){return t instanceof N?t:A(t)?new N(t[0],t[1]):t==null?t:typeof t=="object"&&"x"in t&&"y"in t?new N(t.x,t.y):new N(t,e,i)}function it(t,e){if(t)for(var i=e?[t,e]:t,n=0,o=i.length;n<o;n++)this.extend(i[n])}it.prototype={extend:function(t){var e,i;if(!t)return this;if(t instanceof N||typeof t[0]=="number"||"x"in t)e=i=I(t);else if(t=dt(t),e=t.min,i=t.max,!e||!i)return this;return!this.min&&!this.max?(this.min=e.clone(),this.max=i.clone()):(this.min.x=Math.min(e.x,this.min.x),this.max.x=Math.max(i.x,this.max.x),this.min.y=Math.min(e.y,this.min.y),this.max.y=Math.max(i.y,this.max.y)),this},getCenter:function(t){return I((this.min.x+this.max.x)/2,(this.min.y+this.max.y)/2,t)},getBottomLeft:function(){return I(this.min.x,this.max.y)},getTopRight:function(){return I(this.max.x,this.min.y)},getTopLeft:function(){return this.min},getBottomRight:function(){return this.max},getSize:function(){return this.max.subtract(this.min)},contains:function(t){var e,i;return typeof t[0]=="number"||t instanceof N?t=I(t):t=dt(t),t instanceof it?(e=t.min,i=t.max):e=i=t,e.x>=this.min.x&&i.x<=this.max.x&&e.y>=this.min.y&&i.y<=this.max.y},intersects:function(t){t=dt(t);var e=this.min,i=this.max,n=t.min,o=t.max,r=o.x>=e.x&&n.x<=i.x,c=o.y>=e.y&&n.y<=i.y;return r&&c},overlaps:function(t){t=dt(t);var e=this.min,i=this.max,n=t.min,o=t.max,r=o.x>e.x&&n.x<i.x,c=o.y>e.y&&n.y<i.y;return r&&c},isValid:function(){return!!(this.min&&this.max)},pad:function(t){var e=this.min,i=this.max,n=Math.abs(e.x-i.x)*t,o=Math.abs(e.y-i.y)*t;return dt(I(e.x-n,e.y-o),I(i.x+n,i.y+o))},equals:function(t){return t?(t=dt(t),this.min.equals(t.getTopLeft())&&this.max.equals(t.getBottomRight())):!1}};function dt(t,e){return!t||t instanceof it?t:new it(t,e)}function gt(t,e){if(t)for(var i=e?[t,e]:t,n=0,o=i.length;n<o;n++)this.extend(i[n])}gt.prototype={extend:function(t){var e=this._southWest,i=this._northEast,n,o;if(t instanceof K)n=t,o=t;else if(t instanceof gt){if(n=t._southWest,o=t._northEast,!n||!o)return this}else return t?this.extend(U(t)||rt(t)):this;return!e&&!i?(this._southWest=new K(n.lat,n.lng),this._northEast=new K(o.lat,o.lng)):(e.lat=Math.min(n.lat,e.lat),e.lng=Math.min(n.lng,e.lng),i.lat=Math.max(o.lat,i.lat),i.lng=Math.max(o.lng,i.lng)),this},pad:function(t){var e=this._southWest,i=this._northEast,n=Math.abs(e.lat-i.lat)*t,o=Math.abs(e.lng-i.lng)*t;return new gt(new K(e.lat-n,e.lng-o),new K(i.lat+n,i.lng+o))},getCenter:function(){return new K((this._southWest.lat+this._northEast.lat)/2,(this._southWest.lng+this._northEast.lng)/2)},getSouthWest:function(){return this._southWest},getNorthEast:function(){return this._northEast},getNorthWest:function(){return new K(this.getNorth(),this.getWest())},getSouthEast:function(){return new K(this.getSouth(),this.getEast())},getWest:function(){return this._southWest.lng},getSouth:function(){return this._southWest.lat},getEast:function(){return this._northEast.lng},getNorth:function(){return this._northEast.lat},contains:function(t){typeof t[0]=="number"||t instanceof K||"lat"in t?t=U(t):t=rt(t);var e=this._southWest,i=this._northEast,n,o;return t instanceof gt?(n=t.getSouthWest(),o=t.getNorthEast()):n=o=t,n.lat>=e.lat&&o.lat<=i.lat&&n.lng>=e.lng&&o.lng<=i.lng},intersects:function(t){t=rt(t);var e=this._southWest,i=this._northEast,n=t.getSouthWest(),o=t.getNorthEast(),r=o.lat>=e.lat&&n.lat<=i.lat,c=o.lng>=e.lng&&n.lng<=i.lng;return r&&c},overlaps:function(t){t=rt(t);var e=this._southWest,i=this._northEast,n=t.getSouthWest(),o=t.getNorthEast(),r=o.lat>e.lat&&n.lat<i.lat,c=o.lng>e.lng&&n.lng<i.lng;return r&&c},toBBoxString:function(){return[this.getWest(),this.getSouth(),this.getEast(),this.getNorth()].join(",")},equals:function(t,e){return t?(t=rt(t),this._southWest.equals(t.getSouthWest(),e)&&this._northEast.equals(t.getNorthEast(),e)):!1},isValid:function(){return!!(this._southWest&&this._northEast)}};function rt(t,e){return t instanceof gt?t:new gt(t,e)}function K(t,e,i){if(isNaN(t)||isNaN(e))throw new Error("Invalid LatLng object: ("+t+", "+e+")");this.lat=+t,this.lng=+e,i!==void 0&&(this.alt=+i)}K.prototype={equals:function(t,e){if(!t)return!1;t=U(t);var i=Math.max(Math.abs(this.lat-t.lat),Math.abs(this.lng-t.lng));return i<=(e===void 0?1e-9:e)},toString:function(t){return"LatLng("+C(this.lat,t)+", "+C(this.lng,t)+")"},distanceTo:function(t){return E.distance(this,U(t))},wrap:function(){return E.wrapLatLng(this)},toBounds:function(t){var e=180*t/40075017,i=e/Math.cos(Math.PI/180*this.lat);return rt([this.lat-e,this.lng-i],[this.lat+e,this.lng+i])},clone:function(){return new K(this.lat,this.lng,this.alt)}};function U(t,e,i){return t instanceof K?t:A(t)&&typeof t[0]!="object"?t.length===3?new K(t[0],t[1],t[2]):t.length===2?new K(t[0],t[1]):null:t==null?t:typeof t=="object"&&"lat"in t?new K(t.lat,"lng"in t?t.lng:t.lon,t.alt):e===void 0?null:new K(t,e,i)}var kt={latLngToPoint:function(t,e){var i=this.projection.project(t),n=this.scale(e);return this.transformation._transform(i,n)},pointToLatLng:function(t,e){var i=this.scale(e),n=this.transformation.untransform(t,i);return this.projection.unproject(n)},project:function(t){return this.projection.project(t)},unproject:function(t){return this.projection.unproject(t)},scale:function(t){return 256*Math.pow(2,t)},zoom:function(t){return Math.log(t/256)/Math.LN2},getProjectedBounds:function(t){if(this.infinite)return null;var e=this.projection.bounds,i=this.scale(t),n=this.transformation.transform(e.min,i),o=this.transformation.transform(e.max,i);return new it(n,o)},infinite:!1,wrapLatLng:function(t){var e=this.wrapLng?P(t.lng,this.wrapLng,!0):t.lng,i=this.wrapLat?P(t.lat,this.wrapLat,!0):t.lat,n=t.alt;return new K(i,e,n)},wrapLatLngBounds:function(t){var e=t.getCenter(),i=this.wrapLatLng(e),n=e.lat-i.lat,o=e.lng-i.lng;if(n===0&&o===0)return t;var r=t.getSouthWest(),c=t.getNorthEast(),u=new K(r.lat-n,r.lng-o),m=new K(c.lat-n,c.lng-o);return new gt(u,m)}},E=a({},kt,{wrapLng:[-180,180],R:6371e3,distance:function(t,e){var i=Math.PI/180,n=t.lat*i,o=e.lat*i,r=Math.sin((e.lat-t.lat)*i/2),c=Math.sin((e.lng-t.lng)*i/2),u=r*r+Math.cos(n)*Math.cos(o)*c*c,m=2*Math.atan2(Math.sqrt(u),Math.sqrt(1-u));return this.R*m}}),nt=6378137,ot={R:nt,MAX_LATITUDE:85.0511287798,project:function(t){var e=Math.PI/180,i=this.MAX_LATITUDE,n=Math.max(Math.min(i,t.lat),-i),o=Math.sin(n*e);return new N(this.R*t.lng*e,this.R*Math.log((1+o)/(1-o))/2)},unproject:function(t){var e=180/Math.PI;return new K((2*Math.atan(Math.exp(t.y/this.R))-Math.PI/2)*e,t.x*e/this.R)},bounds:(function(){var t=nt*Math.PI;return new it([-t,-t],[t,t])})()};function At(t,e,i,n){if(A(t)){this._a=t[0],this._b=t[1],this._c=t[2],this._d=t[3];return}this._a=t,this._b=e,this._c=i,this._d=n}At.prototype={transform:function(t,e){return this._transform(t.clone(),e)},_transform:function(t,e){return e=e||1,t.x=e*(this._a*t.x+this._b),t.y=e*(this._c*t.y+this._d),t},untransform:function(t,e){return e=e||1,new N((t.x/e-this._b)/this._a,(t.y/e-this._d)/this._c)}};function tt(t,e,i,n){return new At(t,e,i,n)}var ut=a({},E,{code:"EPSG:3857",projection:ot,transformation:(function(){var t=.5/(Math.PI*ot.R);return tt(t,.5,-t,.5)})()}),Lt=a({},ut,{code:"EPSG:900913"});function Ct(t){return document.createElementNS("http://www.w3.org/2000/svg",t)}function G(t,e){var i="",n,o,r,c,u,m;for(n=0,r=t.length;n<r;n++){for(u=t[n],o=0,c=u.length;o<c;o++)m=u[o],i+=(o?"L":"M")+m.x+" "+m.y;i+=e?S.svg?"z":"x":""}return i||"M0 0"}var Et=document.documentElement.style,Tt="ActiveXObject"in window,ne=Tt&&!document.addEventListener,$t="msLaunchUri"in navigator&&!("documentMode"in document),ti=It("webkit"),Fi=It("android"),Wi=It("android 2")||It("android 3"),_o=parseInt(/WebKit\/([0-9]+)|$/.exec(navigator.userAgent)[1],10),go=Fi&&It("Google")&&_o<537&&!("AudioNode"in window),ei=!!window.opera,qi=!$t&&It("chrome"),Ui=It("gecko")&&!ti&&!ei&&!Tt,vo=!qi&&It("safari"),$i=It("phantom"),Gi="OTransition"in Et,yo=navigator.platform.indexOf("Win")===0,Vi=Tt&&"transition"in Et,ii="WebKitCSSMatrix"in window&&"m11"in new window.WebKitCSSMatrix&&!Wi,ji="MozPerspective"in Et,bo=!window.L_DISABLE_3D&&(Vi||ii||ji)&&!Gi&&!$i,pe=typeof orientation<"u"||It("mobile"),xo=pe&&ti,wo=pe&&ii,Ki=!window.PointerEvent&&window.MSPointerEvent,Yi=!!(window.PointerEvent||Ki),Xi="ontouchstart"in window||!!window.TouchEvent,ko=!window.L_NO_TOUCH&&(Xi||Yi),Po=pe&&ei,Lo=pe&&Ui,Co=(window.devicePixelRatio||window.screen.deviceXDPI/window.screen.logicalXDPI)>1,To=(function(){var t=!1;try{var e=Object.defineProperty({},"passive",{get:function(){t=!0}});window.addEventListener("testPassiveEventSupport",_,e),window.removeEventListener("testPassiveEventSupport",_,e)}catch{}return t})(),Mo=(function(){return!!document.createElement("canvas").getContext})(),ni=!!(document.createElementNS&&Ct("svg").createSVGRect),So=!!ni&&(function(){var t=document.createElement("div");return t.innerHTML="<svg/>",(t.firstChild&&t.firstChild.namespaceURI)==="http://www.w3.org/2000/svg"})(),zo=!ni&&(function(){try{var t=document.createElement("div");t.innerHTML='<v:shape adj="1"/>';var e=t.firstChild;return e.style.behavior="url(#default#VML)",e&&typeof e.adj=="object"}catch{return!1}})(),Ao=navigator.platform.indexOf("Mac")===0,Eo=navigator.platform.indexOf("Linux")===0;function It(t){return navigator.userAgent.toLowerCase().indexOf(t)>=0}var S={ie:Tt,ielt9:ne,edge:$t,webkit:ti,android:Fi,android23:Wi,androidStock:go,opera:ei,chrome:qi,gecko:Ui,safari:vo,phantom:$i,opera12:Gi,win:yo,ie3d:Vi,webkit3d:ii,gecko3d:ji,any3d:bo,mobile:pe,mobileWebkit:xo,mobileWebkit3d:wo,msPointer:Ki,pointer:Yi,touch:ko,touchNative:Xi,mobileOpera:Po,mobileGecko:Lo,retina:Co,passiveEvents:To,canvas:Mo,svg:ni,vml:zo,inlineSvg:So,mac:Ao,linux:Eo},Ji=S.msPointer?"MSPointerDown":"pointerdown",Qi=S.msPointer?"MSPointerMove":"pointermove",tn=S.msPointer?"MSPointerUp":"pointerup",en=S.msPointer?"MSPointerCancel":"pointercancel",oi={touchstart:Ji,touchmove:Qi,touchend:tn,touchcancel:en},nn={touchstart:Ro,touchmove:Se,touchend:Se,touchcancel:Se},oe={},on=!1;function Bo(t,e,i){return e==="touchstart"&&Zo(),nn[e]?(i=nn[e].bind(this,i),t.addEventListener(oi[e],i,!1),i):(console.warn("wrong event specified:",e),_)}function Oo(t,e,i){if(!oi[e]){console.warn("wrong event specified:",e);return}t.removeEventListener(oi[e],i,!1)}function Io(t){oe[t.pointerId]=t}function No(t){oe[t.pointerId]&&(oe[t.pointerId]=t)}function rn(t){delete oe[t.pointerId]}function Zo(){on||(document.addEventListener(Ji,Io,!0),document.addEventListener(Qi,No,!0),document.addEventListener(tn,rn,!0),document.addEventListener(en,rn,!0),on=!0)}function Se(t,e){if(e.pointerType!==(e.MSPOINTER_TYPE_MOUSE||"mouse")){e.touches=[];for(var i in oe)e.touches.push(oe[i]);e.changedTouches=[e],t(e)}}function Ro(t,e){e.MSPOINTER_TYPE_TOUCH&&e.pointerType===e.MSPOINTER_TYPE_TOUCH&&vt(e),Se(t,e)}function Ho(t){var e={},i,n;for(n in t)i=t[n],e[n]=i&&i.bind?i.bind(t):i;return t=e,e.type="dblclick",e.detail=2,e.isTrusted=!1,e._simulated=!0,e}var Do=200;function Fo(t,e){t.addEventListener("dblclick",e);var i=0,n;function o(r){if(r.detail!==1){n=r.detail;return}if(!(r.pointerType==="mouse"||r.sourceCapabilities&&!r.sourceCapabilities.firesTouchEvents)){var c=cn(r);if(!(c.some(function(m){return m instanceof HTMLLabelElement&&m.attributes.for})&&!c.some(function(m){return m instanceof HTMLInputElement||m instanceof HTMLSelectElement}))){var u=Date.now();u-i<=Do?(n++,n===2&&e(Ho(r))):n=1,i=u}}}return t.addEventListener("click",o),{dblclick:e,simDblclick:o}}function Wo(t,e){t.removeEventListener("dblclick",e.dblclick),t.removeEventListener("click",e.simDblclick)}var ri=Ee(["transform","webkitTransform","OTransform","MozTransform","msTransform"]),fe=Ee(["webkitTransition","transition","OTransition","MozTransition","msTransition"]),sn=fe==="webkitTransition"||fe==="OTransition"?fe+"End":"transitionend";function an(t){return typeof t=="string"?document.getElementById(t):t}function me(t,e){var i=t.style[e]||t.currentStyle&&t.currentStyle[e];if((!i||i==="auto")&&document.defaultView){var n=document.defaultView.getComputedStyle(t,null);i=n?n[e]:null}return i==="auto"?null:i}function Y(t,e,i){var n=document.createElement(t);return n.className=e||"",i&&i.appendChild(n),n}function st(t){var e=t.parentNode;e&&e.removeChild(t)}function ze(t){for(;t.firstChild;)t.removeChild(t.firstChild)}function re(t){var e=t.parentNode;e&&e.lastChild!==t&&e.appendChild(t)}function se(t){var e=t.parentNode;e&&e.firstChild!==t&&e.insertBefore(t,e.firstChild)}function si(t,e){if(t.classList!==void 0)return t.classList.contains(e);var i=Ae(t);return i.length>0&&new RegExp("(^|\\s)"+e+"(\\s|$)").test(i)}function W(t,e){if(t.classList!==void 0)for(var i=Z(e),n=0,o=i.length;n<o;n++)t.classList.add(i[n]);else if(!si(t,e)){var r=Ae(t);ai(t,(r?r+" ":"")+e)}}function ht(t,e){t.classList!==void 0?t.classList.remove(e):ai(t,j((" "+Ae(t)+" ").replace(" "+e+" "," ")))}function ai(t,e){t.className.baseVal===void 0?t.className=e:t.className.baseVal=e}function Ae(t){return t.correspondingElement&&(t=t.correspondingElement),t.className.baseVal===void 0?t.className:t.className.baseVal}function Mt(t,e){"opacity"in t.style?t.style.opacity=e:"filter"in t.style&&qo(t,e)}function qo(t,e){var i=!1,n="DXImageTransform.Microsoft.Alpha";try{i=t.filters.item(n)}catch{if(e===1)return}e=Math.round(e*100),i?(i.Enabled=e!==100,i.Opacity=e):t.style.filter+=" progid:"+n+"(opacity="+e+")"}function Ee(t){for(var e=document.documentElement.style,i=0;i<t.length;i++)if(t[i]in e)return t[i];return!1}function Kt(t,e,i){var n=e||new N(0,0);t.style[ri]=(S.ie3d?"translate("+n.x+"px,"+n.y+"px)":"translate3d("+n.x+"px,"+n.y+"px,0)")+(i?" scale("+i+")":"")}function pt(t,e){t._leaflet_pos=e,S.any3d?Kt(t,e):(t.style.left=e.x+"px",t.style.top=e.y+"px")}function Yt(t){return t._leaflet_pos||new N(0,0)}var _e,ge,li;if("onselectstart"in document)_e=function(){R(window,"selectstart",vt)},ge=function(){et(window,"selectstart",vt)};else{var ve=Ee(["userSelect","WebkitUserSelect","OUserSelect","MozUserSelect","msUserSelect"]);_e=function(){if(ve){var t=document.documentElement.style;li=t[ve],t[ve]="none"}},ge=function(){ve&&(document.documentElement.style[ve]=li,li=void 0)}}function hi(){R(window,"dragstart",vt)}function ci(){et(window,"dragstart",vt)}var Be,di;function ui(t){for(;t.tabIndex===-1;)t=t.parentNode;t.style&&(Oe(),Be=t,di=t.style.outlineStyle,t.style.outlineStyle="none",R(window,"keydown",Oe))}function Oe(){Be&&(Be.style.outlineStyle=di,Be=void 0,di=void 0,et(window,"keydown",Oe))}function ln(t){do t=t.parentNode;while((!t.offsetWidth||!t.offsetHeight)&&t!==document.body);return t}function pi(t){var e=t.getBoundingClientRect();return{x:e.width/t.offsetWidth||1,y:e.height/t.offsetHeight||1,boundingClientRect:e}}var Uo={__proto__:null,TRANSFORM:ri,TRANSITION:fe,TRANSITION_END:sn,get:an,getStyle:me,create:Y,remove:st,empty:ze,toFront:re,toBack:se,hasClass:si,addClass:W,removeClass:ht,setClass:ai,getClass:Ae,setOpacity:Mt,testProp:Ee,setTransform:Kt,setPosition:pt,getPosition:Yt,get disableTextSelection(){return _e},get enableTextSelection(){return ge},disableImageDrag:hi,enableImageDrag:ci,preventOutline:ui,restoreOutline:Oe,getSizedParentNode:ln,getScale:pi};function R(t,e,i,n){if(e&&typeof e=="object")for(var o in e)mi(t,o,e[o],i);else{e=Z(e);for(var r=0,c=e.length;r<c;r++)mi(t,e[r],i,n)}return this}var Nt="_leaflet_events";function et(t,e,i,n){if(arguments.length===1)hn(t),delete t[Nt];else if(e&&typeof e=="object")for(var o in e)_i(t,o,e[o],i);else if(e=Z(e),arguments.length===2)hn(t,function(u){return X(e,u)!==-1});else for(var r=0,c=e.length;r<c;r++)_i(t,e[r],i,n);return this}function hn(t,e){for(var i in t[Nt]){var n=i.split(/\d/)[0];(!e||e(n))&&_i(t,n,null,null,i)}}var fi={mouseenter:"mouseover",mouseleave:"mouseout",wheel:!("onwheel"in window)&&"mousewheel"};function mi(t,e,i,n){var o=e+f(i)+(n?"_"+f(n):"");if(t[Nt]&&t[Nt][o])return this;var r=function(u){return i.call(n||t,u||window.event)},c=r;!S.touchNative&&S.pointer&&e.indexOf("touch")===0?r=Bo(t,e,r):S.touch&&e==="dblclick"?r=Fo(t,r):"addEventListener"in t?e==="touchstart"||e==="touchmove"||e==="wheel"||e==="mousewheel"?t.addEventListener(fi[e]||e,r,S.passiveEvents?{passive:!1}:!1):e==="mouseenter"||e==="mouseleave"?(r=function(u){u=u||window.event,vi(t,u)&&c(u)},t.addEventListener(fi[e],r,!1)):t.addEventListener(e,c,!1):t.attachEvent("on"+e,r),t[Nt]=t[Nt]||{},t[Nt][o]=r}function _i(t,e,i,n,o){o=o||e+f(i)+(n?"_"+f(n):"");var r=t[Nt]&&t[Nt][o];if(!r)return this;!S.touchNative&&S.pointer&&e.indexOf("touch")===0?Oo(t,e,r):S.touch&&e==="dblclick"?Wo(t,r):"removeEventListener"in t?t.removeEventListener(fi[e]||e,r,!1):t.detachEvent("on"+e,r),t[Nt][o]=null}function Xt(t){return t.stopPropagation?t.stopPropagation():t.originalEvent?t.originalEvent._stopped=!0:t.cancelBubble=!0,this}function gi(t){return mi(t,"wheel",Xt),this}function ye(t){return R(t,"mousedown touchstart dblclick contextmenu",Xt),t._leaflet_disable_click=!0,this}function vt(t){return t.preventDefault?t.preventDefault():t.returnValue=!1,this}function Jt(t){return vt(t),Xt(t),this}function cn(t){if(t.composedPath)return t.composedPath();for(var e=[],i=t.target;i;)e.push(i),i=i.parentNode;return e}function dn(t,e){if(!e)return new N(t.clientX,t.clientY);var i=pi(e),n=i.boundingClientRect;return new N((t.clientX-n.left)/i.x-e.clientLeft,(t.clientY-n.top)/i.y-e.clientTop)}var $o=S.linux&&S.chrome?window.devicePixelRatio:S.mac?window.devicePixelRatio*3:window.devicePixelRatio>0?2*window.devicePixelRatio:1;function un(t){return S.edge?t.wheelDeltaY/2:t.deltaY&&t.deltaMode===0?-t.deltaY/$o:t.deltaY&&t.deltaMode===1?-t.deltaY*20:t.deltaY&&t.deltaMode===2?-t.deltaY*60:t.deltaX||t.deltaZ?0:t.wheelDelta?(t.wheelDeltaY||t.wheelDelta)/2:t.detail&&Math.abs(t.detail)<32765?-t.detail*20:t.detail?t.detail/-32765*60:0}function vi(t,e){var i=e.relatedTarget;if(!i)return!0;try{for(;i&&i!==t;)i=i.parentNode}catch{return!1}return i!==t}var Go={__proto__:null,on:R,off:et,stopPropagation:Xt,disableScrollPropagation:gi,disableClickPropagation:ye,preventDefault:vt,stop:Jt,getPropagationPath:cn,getMousePosition:dn,getWheelDelta:un,isExternalTarget:vi,addListener:R,removeListener:et},pn=wt.extend({run:function(t,e,i,n){this.stop(),this._el=t,this._inProgress=!0,this._duration=i||.25,this._easeOutPower=1/Math.max(n||.5,.2),this._startPos=Yt(t),this._offset=e.subtract(this._startPos),this._startTime=+new Date,this.fire("start"),this._animate()},stop:function(){this._inProgress&&(this._step(!0),this._complete())},_animate:function(){this._animId=M(this._animate,this),this._step()},_step:function(t){var e=+new Date-this._startTime,i=this._duration*1e3;e<i?this._runFrame(this._easeOut(e/i),t):(this._runFrame(1),this._complete())},_runFrame:function(t,e){var i=this._startPos.add(this._offset.multiplyBy(t));e&&i._round(),pt(this._el,i),this.fire("step")},_complete:function(){y(this._animId),this._inProgress=!1,this.fire("end")},_easeOut:function(t){return 1-Math.pow(1-t,this._easeOutPower)}}),V=wt.extend({options:{crs:ut,center:void 0,zoom:void 0,minZoom:void 0,maxZoom:void 0,layers:[],maxBounds:void 0,renderer:void 0,zoomAnimation:!0,zoomAnimationThreshold:4,fadeAnimation:!0,markerZoomAnimation:!0,transform3DLimit:8388608,zoomSnap:1,zoomDelta:1,trackResize:!0},initialize:function(t,e){e=w(this,e),this._handlers=[],this._layers={},this._zoomBoundLayers={},this._sizeChanged=!0,this._initContainer(t),this._initLayout(),this._onResize=p(this._onResize,this),this._initEvents(),e.maxBounds&&this.setMaxBounds(e.maxBounds),e.zoom!==void 0&&(this._zoom=this._limitZoom(e.zoom)),e.center&&e.zoom!==void 0&&this.setView(U(e.center),e.zoom,{reset:!0}),this.callInitHooks(),this._zoomAnimated=fe&&S.any3d&&!S.mobileOpera&&this.options.zoomAnimation,this._zoomAnimated&&(this._createAnimProxy(),R(this._proxy,sn,this._catchTransitionEnd,this)),this._addLayers(this.options.layers)},setView:function(t,e,i){if(e=e===void 0?this._zoom:this._limitZoom(e),t=this._limitCenter(U(t),e,this.options.maxBounds),i=i||{},this._stop(),this._loaded&&!i.reset&&i!==!0){i.animate!==void 0&&(i.zoom=a({animate:i.animate},i.zoom),i.pan=a({animate:i.animate,duration:i.duration},i.pan));var n=this._zoom!==e?this._tryAnimatedZoom&&this._tryAnimatedZoom(t,e,i.zoom):this._tryAnimatedPan(t,i.pan);if(n)return clearTimeout(this._sizeTimer),this}return this._resetView(t,e,i.pan&&i.pan.noMoveStart),this},setZoom:function(t,e){return this._loaded?this.setView(this.getCenter(),t,{zoom:e}):(this._zoom=t,this)},zoomIn:function(t,e){return t=t||(S.any3d?this.options.zoomDelta:1),this.setZoom(this._zoom+t,e)},zoomOut:function(t,e){return t=t||(S.any3d?this.options.zoomDelta:1),this.setZoom(this._zoom-t,e)},setZoomAround:function(t,e,i){var n=this.getZoomScale(e),o=this.getSize().divideBy(2),r=t instanceof N?t:this.latLngToContainerPoint(t),c=r.subtract(o).multiplyBy(1-1/n),u=this.containerPointToLatLng(o.add(c));return this.setView(u,e,{zoom:i})},_getBoundsCenterZoom:function(t,e){e=e||{},t=t.getBounds?t.getBounds():rt(t);var i=I(e.paddingTopLeft||e.padding||[0,0]),n=I(e.paddingBottomRight||e.padding||[0,0]),o=this.getBoundsZoom(t,!1,i.add(n));if(o=typeof e.maxZoom=="number"?Math.min(e.maxZoom,o):o,o===1/0)return{center:t.getCenter(),zoom:o};var r=n.subtract(i).divideBy(2),c=this.project(t.getSouthWest(),o),u=this.project(t.getNorthEast(),o),m=this.unproject(c.add(u).divideBy(2).add(r),o);return{center:m,zoom:o}},fitBounds:function(t,e){if(t=rt(t),!t.isValid())throw new Error("Bounds are not valid.");var i=this._getBoundsCenterZoom(t,e);return this.setView(i.center,i.zoom,e)},fitWorld:function(t){return this.fitBounds([[-90,-180],[90,180]],t)},panTo:function(t,e){return this.setView(t,this._zoom,{pan:e})},panBy:function(t,e){if(t=I(t).round(),e=e||{},!t.x&&!t.y)return this.fire("moveend");if(e.animate!==!0&&!this.getSize().contains(t))return this._resetView(this.unproject(this.project(this.getCenter()).add(t)),this.getZoom()),this;if(this._panAnim||(this._panAnim=new pn,this._panAnim.on({step:this._onPanTransitionStep,end:this._onPanTransitionEnd},this)),e.noMoveStart||this.fire("movestart"),e.animate!==!1){W(this._mapPane,"leaflet-pan-anim");var i=this._getMapPanePos().subtract(t).round();this._panAnim.run(this._mapPane,i,e.duration||.25,e.easeLinearity)}else this._rawPanBy(t),this.fire("move").fire("moveend");return this},flyTo:function(t,e,i){if(i=i||{},i.animate===!1||!S.any3d)return this.setView(t,e,i);this._stop();var n=this.project(this.getCenter()),o=this.project(t),r=this.getSize(),c=this._zoom;t=U(t),e=e===void 0?c:e;var u=Math.max(r.x,r.y),m=u*this.getZoomScale(c,e),v=o.distanceTo(n)||1,k=1.42,B=k*k;function $(ft){var Ge=ft?-1:1,Or=ft?m:u,Ir=m*m-u*u+Ge*B*B*v*v,Nr=2*Or*B*v,Si=Ir/Nr,Vn=Math.sqrt(Si*Si+1)-Si,Zr=Vn<1e-9?-18:Math.log(Vn);return Zr}function bt(ft){return(Math.exp(ft)-Math.exp(-ft))/2}function mt(ft){return(Math.exp(ft)+Math.exp(-ft))/2}function zt(ft){return bt(ft)/mt(ft)}var xt=$(0);function ue(ft){return u*(mt(xt)/mt(xt+k*ft))}function zr(ft){return u*(mt(xt)*zt(xt+k*ft)-bt(xt))/B}function Ar(ft){return 1-Math.pow(1-ft,1.5)}var Er=Date.now(),$n=($(1)-xt)/k,Br=i.duration?1e3*i.duration:1e3*$n*.8;function Gn(){var ft=(Date.now()-Er)/Br,Ge=Ar(ft)*$n;ft<=1?(this._flyToFrame=M(Gn,this),this._move(this.unproject(n.add(o.subtract(n).multiplyBy(zr(Ge)/v)),c),this.getScaleZoom(u/ue(Ge),c),{flyTo:!0})):this._move(t,e)._moveEnd(!0)}return this._moveStart(!0,i.noMoveStart),Gn.call(this),this},flyToBounds:function(t,e){var i=this._getBoundsCenterZoom(t,e);return this.flyTo(i.center,i.zoom,e)},setMaxBounds:function(t){return t=rt(t),this.listens("moveend",this._panInsideMaxBounds)&&this.off("moveend",this._panInsideMaxBounds),t.isValid()?(this.options.maxBounds=t,this._loaded&&this._panInsideMaxBounds(),this.on("moveend",this._panInsideMaxBounds)):(this.options.maxBounds=null,this)},setMinZoom:function(t){var e=this.options.minZoom;return this.options.minZoom=t,this._loaded&&e!==t&&(this.fire("zoomlevelschange"),this.getZoom()<this.options.minZoom)?this.setZoom(t):this},setMaxZoom:function(t){var e=this.options.maxZoom;return this.options.maxZoom=t,this._loaded&&e!==t&&(this.fire("zoomlevelschange"),this.getZoom()>this.options.maxZoom)?this.setZoom(t):this},panInsideBounds:function(t,e){this._enforcingBounds=!0;var i=this.getCenter(),n=this._limitCenter(i,this._zoom,rt(t));return i.equals(n)||this.panTo(n,e),this._enforcingBounds=!1,this},panInside:function(t,e){e=e||{};var i=I(e.paddingTopLeft||e.padding||[0,0]),n=I(e.paddingBottomRight||e.padding||[0,0]),o=this.project(this.getCenter()),r=this.project(t),c=this.getPixelBounds(),u=dt([c.min.add(i),c.max.subtract(n)]),m=u.getSize();if(!u.contains(r)){this._enforcingBounds=!0;var v=r.subtract(u.getCenter()),k=u.extend(r).getSize().subtract(m);o.x+=v.x<0?-k.x:k.x,o.y+=v.y<0?-k.y:k.y,this.panTo(this.unproject(o),e),this._enforcingBounds=!1}return this},invalidateSize:function(t){if(!this._loaded)return this;t=a({animate:!1,pan:!0},t===!0?{animate:!0}:t);var e=this.getSize();this._sizeChanged=!0,this._lastCenter=null;var i=this.getSize(),n=e.divideBy(2).round(),o=i.divideBy(2).round(),r=n.subtract(o);return!r.x&&!r.y?this:(t.animate&&t.pan?this.panBy(r):(t.pan&&this._rawPanBy(r),this.fire("move"),t.debounceMoveend?(clearTimeout(this._sizeTimer),this._sizeTimer=setTimeout(p(this.fire,this,"moveend"),200)):this.fire("moveend")),this.fire("resize",{oldSize:e,newSize:i}))},stop:function(){return this.setZoom(this._limitZoom(this._zoom)),this.options.zoomSnap||this.fire("viewreset"),this._stop()},locate:function(t){if(t=this._locateOptions=a({timeout:1e4,watch:!1},t),!("geolocation"in navigator))return this._handleGeolocationError({code:0,message:"Geolocation not supported."}),this;var e=p(this._handleGeolocationResponse,this),i=p(this._handleGeolocationError,this);return t.watch?this._locationWatchId=navigator.geolocation.watchPosition(e,i,t):navigator.geolocation.getCurrentPosition(e,i,t),this},stopLocate:function(){return navigator.geolocation&&navigator.geolocation.clearWatch&&navigator.geolocation.clearWatch(this._locationWatchId),this._locateOptions&&(this._locateOptions.setView=!1),this},_handleGeolocationError:function(t){if(this._container._leaflet_id){var e=t.code,i=t.message||(e===1?"permission denied":e===2?"position unavailable":"timeout");this._locateOptions.setView&&!this._loaded&&this.fitWorld(),this.fire("locationerror",{code:e,message:"Geolocation error: "+i+"."})}},_handleGeolocationResponse:function(t){if(this._container._leaflet_id){var e=t.coords.latitude,i=t.coords.longitude,n=new K(e,i),o=n.toBounds(t.coords.accuracy*2),r=this._locateOptions;if(r.setView){var c=this.getBoundsZoom(o);this.setView(n,r.maxZoom?Math.min(c,r.maxZoom):c)}var u={latlng:n,bounds:o,timestamp:t.timestamp};for(var m in t.coords)typeof t.coords[m]=="number"&&(u[m]=t.coords[m]);this.fire("locationfound",u)}},addHandler:function(t,e){if(!e)return this;var i=this[t]=new e(this);return this._handlers.push(i),this.options[t]&&i.enable(),this},remove:function(){if(this._initEvents(!0),this.options.maxBounds&&this.off("moveend",this._panInsideMaxBounds),this._containerId!==this._container._leaflet_id)throw new Error("Map container is being reused by another instance");try{delete this._container._leaflet_id,delete this._containerId}catch{this._container._leaflet_id=void 0,this._containerId=void 0}this._locationWatchId!==void 0&&this.stopLocate(),this._stop(),st(this._mapPane),this._clearControlPos&&this._clearControlPos(),this._resizeRequest&&(y(this._resizeRequest),this._resizeRequest=null),this._clearHandlers(),this._loaded&&this.fire("unload");var t;for(t in this._layers)this._layers[t].remove();for(t in this._panes)st(this._panes[t]);return this._layers=[],this._panes=[],delete this._mapPane,delete this._renderer,this},createPane:function(t,e){var i="leaflet-pane"+(t?" leaflet-"+t.replace("Pane","")+"-pane":""),n=Y("div",i,e||this._mapPane);return t&&(this._panes[t]=n),n},getCenter:function(){return this._checkIfLoaded(),this._lastCenter&&!this._moved()?this._lastCenter.clone():this.layerPointToLatLng(this._getCenterLayerPoint())},getZoom:function(){return this._zoom},getBounds:function(){var t=this.getPixelBounds(),e=this.unproject(t.getBottomLeft()),i=this.unproject(t.getTopRight());return new gt(e,i)},getMinZoom:function(){return this.options.minZoom===void 0?this._layersMinZoom||0:this.options.minZoom},getMaxZoom:function(){return this.options.maxZoom===void 0?this._layersMaxZoom===void 0?1/0:this._layersMaxZoom:this.options.maxZoom},getBoundsZoom:function(t,e,i){t=rt(t),i=I(i||[0,0]);var n=this.getZoom()||0,o=this.getMinZoom(),r=this.getMaxZoom(),c=t.getNorthWest(),u=t.getSouthEast(),m=this.getSize().subtract(i),v=dt(this.project(u,n),this.project(c,n)).getSize(),k=S.any3d?this.options.zoomSnap:1,B=m.x/v.x,$=m.y/v.y,bt=e?Math.max(B,$):Math.min(B,$);return n=this.getScaleZoom(bt,n),k&&(n=Math.round(n/(k/100))*(k/100),n=e?Math.ceil(n/k)*k:Math.floor(n/k)*k),Math.max(o,Math.min(r,n))},getSize:function(){return(!this._size||this._sizeChanged)&&(this._size=new N(this._container.clientWidth||0,this._container.clientHeight||0),this._sizeChanged=!1),this._size.clone()},getPixelBounds:function(t,e){var i=this._getTopLeftPoint(t,e);return new it(i,i.add(this.getSize()))},getPixelOrigin:function(){return this._checkIfLoaded(),this._pixelOrigin},getPixelWorldBounds:function(t){return this.options.crs.getProjectedBounds(t===void 0?this.getZoom():t)},getPane:function(t){return typeof t=="string"?this._panes[t]:t},getPanes:function(){return this._panes},getContainer:function(){return this._container},getZoomScale:function(t,e){var i=this.options.crs;return e=e===void 0?this._zoom:e,i.scale(t)/i.scale(e)},getScaleZoom:function(t,e){var i=this.options.crs;e=e===void 0?this._zoom:e;var n=i.zoom(t*i.scale(e));return isNaN(n)?1/0:n},project:function(t,e){return e=e===void 0?this._zoom:e,this.options.crs.latLngToPoint(U(t),e)},unproject:function(t,e){return e=e===void 0?this._zoom:e,this.options.crs.pointToLatLng(I(t),e)},layerPointToLatLng:function(t){var e=I(t).add(this.getPixelOrigin());return this.unproject(e)},latLngToLayerPoint:function(t){var e=this.project(U(t))._round();return e._subtract(this.getPixelOrigin())},wrapLatLng:function(t){return this.options.crs.wrapLatLng(U(t))},wrapLatLngBounds:function(t){return this.options.crs.wrapLatLngBounds(rt(t))},distance:function(t,e){return this.options.crs.distance(U(t),U(e))},containerPointToLayerPoint:function(t){return I(t).subtract(this._getMapPanePos())},layerPointToContainerPoint:function(t){return I(t).add(this._getMapPanePos())},containerPointToLatLng:function(t){var e=this.containerPointToLayerPoint(I(t));return this.layerPointToLatLng(e)},latLngToContainerPoint:function(t){return this.layerPointToContainerPoint(this.latLngToLayerPoint(U(t)))},mouseEventToContainerPoint:function(t){return dn(t,this._container)},mouseEventToLayerPoint:function(t){return this.containerPointToLayerPoint(this.mouseEventToContainerPoint(t))},mouseEventToLatLng:function(t){return this.layerPointToLatLng(this.mouseEventToLayerPoint(t))},_initContainer:function(t){var e=this._container=an(t);if(e){if(e._leaflet_id)throw new Error("Map container is already initialized.")}else throw new Error("Map container not found.");R(e,"scroll",this._onScroll,this),this._containerId=f(e)},_initLayout:function(){var t=this._container;this._fadeAnimated=this.options.fadeAnimation&&S.any3d,W(t,"leaflet-container"+(S.touch?" leaflet-touch":"")+(S.retina?" leaflet-retina":"")+(S.ielt9?" leaflet-oldie":"")+(S.safari?" leaflet-safari":"")+(this._fadeAnimated?" leaflet-fade-anim":""));var e=me(t,"position");e!=="absolute"&&e!=="relative"&&e!=="fixed"&&e!=="sticky"&&(t.style.position="relative"),this._initPanes(),this._initControlPos&&this._initControlPos()},_initPanes:function(){var t=this._panes={};this._paneRenderers={},this._mapPane=this.createPane("mapPane",this._container),pt(this._mapPane,new N(0,0)),this.createPane("tilePane"),this.createPane("overlayPane"),this.createPane("shadowPane"),this.createPane("markerPane"),this.createPane("tooltipPane"),this.createPane("popupPane"),this.options.markerZoomAnimation||(W(t.markerPane,"leaflet-zoom-hide"),W(t.shadowPane,"leaflet-zoom-hide"))},_resetView:function(t,e,i){pt(this._mapPane,new N(0,0));var n=!this._loaded;this._loaded=!0,e=this._limitZoom(e),this.fire("viewprereset");var o=this._zoom!==e;this._moveStart(o,i)._move(t,e)._moveEnd(o),this.fire("viewreset"),n&&this.fire("load")},_moveStart:function(t,e){return t&&this.fire("zoomstart"),e||this.fire("movestart"),this},_move:function(t,e,i,n){e===void 0&&(e=this._zoom);var o=this._zoom!==e;return this._zoom=e,this._lastCenter=t,this._pixelOrigin=this._getNewPixelOrigin(t),n?i&&i.pinch&&this.fire("zoom",i):((o||i&&i.pinch)&&this.fire("zoom",i),this.fire("move",i)),this},_moveEnd:function(t){return t&&this.fire("zoomend"),this.fire("moveend")},_stop:function(){return y(this._flyToFrame),this._panAnim&&this._panAnim.stop(),this},_rawPanBy:function(t){pt(this._mapPane,this._getMapPanePos().subtract(t))},_getZoomSpan:function(){return this.getMaxZoom()-this.getMinZoom()},_panInsideMaxBounds:function(){this._enforcingBounds||this.panInsideBounds(this.options.maxBounds)},_checkIfLoaded:function(){if(!this._loaded)throw new Error("Set map center and zoom first.")},_initEvents:function(t){this._targets={},this._targets[f(this._container)]=this;var e=t?et:R;e(this._container,"click dblclick mousedown mouseup mouseover mouseout mousemove contextmenu keypress keydown keyup",this._handleDOMEvent,this),this.options.trackResize&&e(window,"resize",this._onResize,this),S.any3d&&this.options.transform3DLimit&&(t?this.off:this.on).call(this,"moveend",this._onMoveEnd)},_onResize:function(){y(this._resizeRequest),this._resizeRequest=M(function(){this.invalidateSize({debounceMoveend:!0})},this)},_onScroll:function(){this._container.scrollTop=0,this._container.scrollLeft=0},_onMoveEnd:function(){var t=this._getMapPanePos();Math.max(Math.abs(t.x),Math.abs(t.y))>=this.options.transform3DLimit&&this._resetView(this.getCenter(),this.getZoom())},_findEventTargets:function(t,e){for(var i=[],n,o=e==="mouseout"||e==="mouseover",r=t.target||t.srcElement,c=!1;r;){if(n=this._targets[f(r)],n&&(e==="click"||e==="preclick")&&this._draggableMoved(n)){c=!0;break}if(n&&n.listens(e,!0)&&(o&&!vi(r,t)||(i.push(n),o))||r===this._container)break;r=r.parentNode}return!i.length&&!c&&!o&&this.listens(e,!0)&&(i=[this]),i},_isClickDisabled:function(t){for(;t&&t!==this._container;){if(t._leaflet_disable_click)return!0;t=t.parentNode}},_handleDOMEvent:function(t){var e=t.target||t.srcElement;if(!(!this._loaded||e._leaflet_disable_events||t.type==="click"&&this._isClickDisabled(e))){var i=t.type;i==="mousedown"&&ui(e),this._fireDOMEvent(t,i)}},_mouseEvents:["click","dblclick","mouseover","mouseout","contextmenu"],_fireDOMEvent:function(t,e,i){if(t.type==="click"){var n=a({},t);n.type="preclick",this._fireDOMEvent(n,n.type,i)}var o=this._findEventTargets(t,e);if(i){for(var r=[],c=0;c<i.length;c++)i[c].listens(e,!0)&&r.push(i[c]);o=r.concat(o)}if(o.length){e==="contextmenu"&&vt(t);var u=o[0],m={originalEvent:t};if(t.type!=="keypress"&&t.type!=="keydown"&&t.type!=="keyup"){var v=u.getLatLng&&(!u._radius||u._radius<=10);m.containerPoint=v?this.latLngToContainerPoint(u.getLatLng()):this.mouseEventToContainerPoint(t),m.layerPoint=this.containerPointToLayerPoint(m.containerPoint),m.latlng=v?u.getLatLng():this.layerPointToLatLng(m.layerPoint)}for(c=0;c<o.length;c++)if(o[c].fire(e,m,!0),m.originalEvent._stopped||o[c].options.bubblingMouseEvents===!1&&X(this._mouseEvents,e)!==-1)return}},_draggableMoved:function(t){return t=t.dragging&&t.dragging.enabled()?t:this,t.dragging&&t.dragging.moved()||this.boxZoom&&this.boxZoom.moved()},_clearHandlers:function(){for(var t=0,e=this._handlers.length;t<e;t++)this._handlers[t].disable()},whenReady:function(t,e){return this._loaded?t.call(e||this,{target:this}):this.on("load",t,e),this},_getMapPanePos:function(){return Yt(this._mapPane)||new N(0,0)},_moved:function(){var t=this._getMapPanePos();return t&&!t.equals([0,0])},_getTopLeftPoint:function(t,e){var i=t&&e!==void 0?this._getNewPixelOrigin(t,e):this.getPixelOrigin();return i.subtract(this._getMapPanePos())},_getNewPixelOrigin:function(t,e){var i=this.getSize()._divideBy(2);return this.project(t,e)._subtract(i)._add(this._getMapPanePos())._round()},_latLngToNewLayerPoint:function(t,e,i){var n=this._getNewPixelOrigin(i,e);return this.project(t,e)._subtract(n)},_latLngBoundsToNewLayerBounds:function(t,e,i){var n=this._getNewPixelOrigin(i,e);return dt([this.project(t.getSouthWest(),e)._subtract(n),this.project(t.getNorthWest(),e)._subtract(n),this.project(t.getSouthEast(),e)._subtract(n),this.project(t.getNorthEast(),e)._subtract(n)])},_getCenterLayerPoint:function(){return this.containerPointToLayerPoint(this.getSize()._divideBy(2))},_getCenterOffset:function(t){return this.latLngToLayerPoint(t).subtract(this._getCenterLayerPoint())},_limitCenter:function(t,e,i){if(!i)return t;var n=this.project(t,e),o=this.getSize().divideBy(2),r=new it(n.subtract(o),n.add(o)),c=this._getBoundsOffset(r,i,e);return Math.abs(c.x)<=1&&Math.abs(c.y)<=1?t:this.unproject(n.add(c),e)},_limitOffset:function(t,e){if(!e)return t;var i=this.getPixelBounds(),n=new it(i.min.add(t),i.max.add(t));return t.add(this._getBoundsOffset(n,e))},_getBoundsOffset:function(t,e,i){var n=dt(this.project(e.getNorthEast(),i),this.project(e.getSouthWest(),i)),o=n.min.subtract(t.min),r=n.max.subtract(t.max),c=this._rebound(o.x,-r.x),u=this._rebound(o.y,-r.y);return new N(c,u)},_rebound:function(t,e){return t+e>0?Math.round(t-e)/2:Math.max(0,Math.ceil(t))-Math.max(0,Math.floor(e))},_limitZoom:function(t){var e=this.getMinZoom(),i=this.getMaxZoom(),n=S.any3d?this.options.zoomSnap:1;return n&&(t=Math.round(t/n)*n),Math.max(e,Math.min(i,t))},_onPanTransitionStep:function(){this.fire("move")},_onPanTransitionEnd:function(){ht(this._mapPane,"leaflet-pan-anim"),this.fire("moveend")},_tryAnimatedPan:function(t,e){var i=this._getCenterOffset(t)._trunc();return(e&&e.animate)!==!0&&!this.getSize().contains(i)?!1:(this.panBy(i,e),!0)},_createAnimProxy:function(){var t=this._proxy=Y("div","leaflet-proxy leaflet-zoom-animated");this._panes.mapPane.appendChild(t),this.on("zoomanim",function(e){var i=ri,n=this._proxy.style[i];Kt(this._proxy,this.project(e.center,e.zoom),this.getZoomScale(e.zoom,1)),n===this._proxy.style[i]&&this._animatingZoom&&this._onZoomTransitionEnd()},this),this.on("load moveend",this._animMoveEnd,this),this._on("unload",this._destroyAnimProxy,this)},_destroyAnimProxy:function(){st(this._proxy),this.off("load moveend",this._animMoveEnd,this),delete this._proxy},_animMoveEnd:function(){var t=this.getCenter(),e=this.getZoom();Kt(this._proxy,this.project(t,e),this.getZoomScale(e,1))},_catchTransitionEnd:function(t){this._animatingZoom&&t.propertyName.indexOf("transform")>=0&&this._onZoomTransitionEnd()},_nothingToAnimate:function(){return!this._container.getElementsByClassName("leaflet-zoom-animated").length},_tryAnimatedZoom:function(t,e,i){if(this._animatingZoom)return!0;if(i=i||{},!this._zoomAnimated||i.animate===!1||this._nothingToAnimate()||Math.abs(e-this._zoom)>this.options.zoomAnimationThreshold)return!1;var n=this.getZoomScale(e),o=this._getCenterOffset(t)._divideBy(1-1/n);return i.animate!==!0&&!this.getSize().contains(o)?!1:(M(function(){this._moveStart(!0,i.noMoveStart||!1)._animateZoom(t,e,!0)},this),!0)},_animateZoom:function(t,e,i,n){this._mapPane&&(i&&(this._animatingZoom=!0,this._animateToCenter=t,this._animateToZoom=e,W(this._mapPane,"leaflet-zoom-anim")),this.fire("zoomanim",{center:t,zoom:e,noUpdate:n}),this._tempFireZoomEvent||(this._tempFireZoomEvent=this._zoom!==this._animateToZoom),this._move(this._animateToCenter,this._animateToZoom,void 0,!0),setTimeout(p(this._onZoomTransitionEnd,this),250))},_onZoomTransitionEnd:function(){this._animatingZoom&&(this._mapPane&&ht(this._mapPane,"leaflet-zoom-anim"),this._animatingZoom=!1,this._move(this._animateToCenter,this._animateToZoom,void 0,!0),this._tempFireZoomEvent&&this.fire("zoom"),delete this._tempFireZoomEvent,this.fire("move"),this._moveEnd(!0))}});function Vo(t,e){return new V(t,e)}var Bt=Q.extend({options:{position:"topright"},initialize:function(t){w(this,t)},getPosition:function(){return this.options.position},setPosition:function(t){var e=this._map;return e&&e.removeControl(this),this.options.position=t,e&&e.addControl(this),this},getContainer:function(){return this._container},addTo:function(t){this.remove(),this._map=t;var e=this._container=this.onAdd(t),i=this.getPosition(),n=t._controlCorners[i];return W(e,"leaflet-control"),i.indexOf("bottom")!==-1?n.insertBefore(e,n.firstChild):n.appendChild(e),this._map.on("unload",this.remove,this),this},remove:function(){return this._map?(st(this._container),this.onRemove&&this.onRemove(this._map),this._map.off("unload",this.remove,this),this._map=null,this):this},_refocusOnMap:function(t){this._map&&t&&t.screenX>0&&t.screenY>0&&this._map.getContainer().focus()}}),be=function(t){return new Bt(t)};V.include({addControl:function(t){return t.addTo(this),this},removeControl:function(t){return t.remove(),this},_initControlPos:function(){var t=this._controlCorners={},e="leaflet-",i=this._controlContainer=Y("div",e+"control-container",this._container);function n(o,r){var c=e+o+" "+e+r;t[o+r]=Y("div",c,i)}n("top","left"),n("top","right"),n("bottom","left"),n("bottom","right")},_clearControlPos:function(){for(var t in this._controlCorners)st(this._controlCorners[t]);st(this._controlContainer),delete this._controlCorners,delete this._controlContainer}});var fn=Bt.extend({options:{collapsed:!0,position:"topright",autoZIndex:!0,hideSingleBase:!1,sortLayers:!1,sortFunction:function(t,e,i,n){return i<n?-1:n<i?1:0}},initialize:function(t,e,i){w(this,i),this._layerControlInputs=[],this._layers=[],this._lastZIndex=0,this._handlingClick=!1,this._preventClick=!1;for(var n in t)this._addLayer(t[n],n);for(n in e)this._addLayer(e[n],n,!0)},onAdd:function(t){this._initLayout(),this._update(),this._map=t,t.on("zoomend",this._checkDisabledLayers,this);for(var e=0;e<this._layers.length;e++)this._layers[e].layer.on("add remove",this._onLayerChange,this);return this._container},addTo:function(t){return Bt.prototype.addTo.call(this,t),this._expandIfNotCollapsed()},onRemove:function(){this._map.off("zoomend",this._checkDisabledLayers,this);for(var t=0;t<this._layers.length;t++)this._layers[t].layer.off("add remove",this._onLayerChange,this)},addBaseLayer:function(t,e){return this._addLayer(t,e),this._map?this._update():this},addOverlay:function(t,e){return this._addLayer(t,e,!0),this._map?this._update():this},removeLayer:function(t){t.off("add remove",this._onLayerChange,this);var e=this._getLayer(f(t));return e&&this._layers.splice(this._layers.indexOf(e),1),this._map?this._update():this},expand:function(){W(this._container,"leaflet-control-layers-expanded"),this._section.style.height=null;var t=this._map.getSize().y-(this._container.offsetTop+50);return t<this._section.clientHeight?(W(this._section,"leaflet-control-layers-scrollbar"),this._section.style.height=t+"px"):ht(this._section,"leaflet-control-layers-scrollbar"),this._checkDisabledLayers(),this},collapse:function(){return ht(this._container,"leaflet-control-layers-expanded"),this},_initLayout:function(){var t="leaflet-control-layers",e=this._container=Y("div",t),i=this.options.collapsed;e.setAttribute("aria-haspopup",!0),ye(e),gi(e);var n=this._section=Y("section",t+"-list");i&&(this._map.on("click",this.collapse,this),R(e,{mouseenter:this._expandSafely,mouseleave:this.collapse},this));var o=this._layersLink=Y("a",t+"-toggle",e);o.href="#",o.title="Layers",o.setAttribute("role","button"),R(o,{keydown:function(r){r.keyCode===13&&this._expandSafely()},click:function(r){vt(r),this._expandSafely()}},this),i||this.expand(),this._baseLayersList=Y("div",t+"-base",n),this._separator=Y("div",t+"-separator",n),this._overlaysList=Y("div",t+"-overlays",n),e.appendChild(n)},_getLayer:function(t){for(var e=0;e<this._layers.length;e++)if(this._layers[e]&&f(this._layers[e].layer)===t)return this._layers[e]},_addLayer:function(t,e,i){this._map&&t.on("add remove",this._onLayerChange,this),this._layers.push({layer:t,name:e,overlay:i}),this.options.sortLayers&&this._layers.sort(p(function(n,o){return this.options.sortFunction(n.layer,o.layer,n.name,o.name)},this)),this.options.autoZIndex&&t.setZIndex&&(this._lastZIndex++,t.setZIndex(this._lastZIndex)),this._expandIfNotCollapsed()},_update:function(){if(!this._container)return this;ze(this._baseLayersList),ze(this._overlaysList),this._layerControlInputs=[];var t,e,i,n,o=0;for(i=0;i<this._layers.length;i++)n=this._layers[i],this._addItem(n),e=e||n.overlay,t=t||!n.overlay,o+=n.overlay?0:1;return this.options.hideSingleBase&&(t=t&&o>1,this._baseLayersList.style.display=t?"":"none"),this._separator.style.display=e&&t?"":"none",this},_onLayerChange:function(t){this._handlingClick||this._update();var e=this._getLayer(f(t.target)),i=e.overlay?t.type==="add"?"overlayadd":"overlayremove":t.type==="add"?"baselayerchange":null;i&&this._map.fire(i,e)},_createRadioElement:function(t,e){var i='<input type="radio" class="leaflet-control-layers-selector" name="'+t+'"'+(e?' checked="checked"':"")+"/>",n=document.createElement("div");return n.innerHTML=i,n.firstChild},_addItem:function(t){var e=document.createElement("label"),i=this._map.hasLayer(t.layer),n;t.overlay?(n=document.createElement("input"),n.type="checkbox",n.className="leaflet-control-layers-selector",n.defaultChecked=i):n=this._createRadioElement("leaflet-base-layers_"+f(this),i),this._layerControlInputs.push(n),n.layerId=f(t.layer),R(n,"click",this._onInputClick,this);var o=document.createElement("span");o.innerHTML=" "+t.name;var r=document.createElement("span");e.appendChild(r),r.appendChild(n),r.appendChild(o);var c=t.overlay?this._overlaysList:this._baseLayersList;return c.appendChild(e),this._checkDisabledLayers(),e},_onInputClick:function(){if(!this._preventClick){var t=this._layerControlInputs,e,i,n=[],o=[];this._handlingClick=!0;for(var r=t.length-1;r>=0;r--)e=t[r],i=this._getLayer(e.layerId).layer,e.checked?n.push(i):e.checked||o.push(i);for(r=0;r<o.length;r++)this._map.hasLayer(o[r])&&this._map.removeLayer(o[r]);for(r=0;r<n.length;r++)this._map.hasLayer(n[r])||this._map.addLayer(n[r]);this._handlingClick=!1,this._refocusOnMap()}},_checkDisabledLayers:function(){for(var t=this._layerControlInputs,e,i,n=this._map.getZoom(),o=t.length-1;o>=0;o--)e=t[o],i=this._getLayer(e.layerId).layer,e.disabled=i.options.minZoom!==void 0&&n<i.options.minZoom||i.options.maxZoom!==void 0&&n>i.options.maxZoom},_expandIfNotCollapsed:function(){return this._map&&!this.options.collapsed&&this.expand(),this},_expandSafely:function(){var t=this._section;this._preventClick=!0,R(t,"click",vt),this.expand();var e=this;setTimeout(function(){et(t,"click",vt),e._preventClick=!1})}}),jo=function(t,e,i){return new fn(t,e,i)},yi=Bt.extend({options:{position:"topleft",zoomInText:'<span aria-hidden="true">+</span>',zoomInTitle:"Zoom in",zoomOutText:'<span aria-hidden="true">&#x2212;</span>',zoomOutTitle:"Zoom out"},onAdd:function(t){var e="leaflet-control-zoom",i=Y("div",e+" leaflet-bar"),n=this.options;return this._zoomInButton=this._createButton(n.zoomInText,n.zoomInTitle,e+"-in",i,this._zoomIn),this._zoomOutButton=this._createButton(n.zoomOutText,n.zoomOutTitle,e+"-out",i,this._zoomOut),this._updateDisabled(),t.on("zoomend zoomlevelschange",this._updateDisabled,this),i},onRemove:function(t){t.off("zoomend zoomlevelschange",this._updateDisabled,this)},disable:function(){return this._disabled=!0,this._updateDisabled(),this},enable:function(){return this._disabled=!1,this._updateDisabled(),this},_zoomIn:function(t){!this._disabled&&this._map._zoom<this._map.getMaxZoom()&&this._map.zoomIn(this._map.options.zoomDelta*(t.shiftKey?3:1))},_zoomOut:function(t){!this._disabled&&this._map._zoom>this._map.getMinZoom()&&this._map.zoomOut(this._map.options.zoomDelta*(t.shiftKey?3:1))},_createButton:function(t,e,i,n,o){var r=Y("a",i,n);return r.innerHTML=t,r.href="#",r.title=e,r.setAttribute("role","button"),r.setAttribute("aria-label",e),ye(r),R(r,"click",Jt),R(r,"click",o,this),R(r,"click",this._refocusOnMap,this),r},_updateDisabled:function(){var t=this._map,e="leaflet-disabled";ht(this._zoomInButton,e),ht(this._zoomOutButton,e),this._zoomInButton.setAttribute("aria-disabled","false"),this._zoomOutButton.setAttribute("aria-disabled","false"),(this._disabled||t._zoom===t.getMinZoom())&&(W(this._zoomOutButton,e),this._zoomOutButton.setAttribute("aria-disabled","true")),(this._disabled||t._zoom===t.getMaxZoom())&&(W(this._zoomInButton,e),this._zoomInButton.setAttribute("aria-disabled","true"))}});V.mergeOptions({zoomControl:!0}),V.addInitHook(function(){this.options.zoomControl&&(this.zoomControl=new yi,this.addControl(this.zoomControl))});var Ko=function(t){return new yi(t)},mn=Bt.extend({options:{position:"bottomleft",maxWidth:100,metric:!0,imperial:!0},onAdd:function(t){var e="leaflet-control-scale",i=Y("div",e),n=this.options;return this._addScales(n,e+"-line",i),t.on(n.updateWhenIdle?"moveend":"move",this._update,this),t.whenReady(this._update,this),i},onRemove:function(t){t.off(this.options.updateWhenIdle?"moveend":"move",this._update,this)},_addScales:function(t,e,i){t.metric&&(this._mScale=Y("div",e,i)),t.imperial&&(this._iScale=Y("div",e,i))},_update:function(){var t=this._map,e=t.getSize().y/2,i=t.distance(t.containerPointToLatLng([0,e]),t.containerPointToLatLng([this.options.maxWidth,e]));this._updateScales(i)},_updateScales:function(t){this.options.metric&&t&&this._updateMetric(t),this.options.imperial&&t&&this._updateImperial(t)},_updateMetric:function(t){var e=this._getRoundNum(t),i=e<1e3?e+" m":e/1e3+" km";this._updateScale(this._mScale,i,e/t)},_updateImperial:function(t){var e=t*3.2808399,i,n,o;e>5280?(i=e/5280,n=this._getRoundNum(i),this._updateScale(this._iScale,n+" mi",n/i)):(o=this._getRoundNum(e),this._updateScale(this._iScale,o+" ft",o/e))},_updateScale:function(t,e,i){t.style.width=Math.round(this.options.maxWidth*i)+"px",t.innerHTML=e},_getRoundNum:function(t){var e=Math.pow(10,(Math.floor(t)+"").length-1),i=t/e;return i=i>=10?10:i>=5?5:i>=3?3:i>=2?2:1,e*i}}),Yo=function(t){return new mn(t)},Xo='<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8" class="leaflet-attribution-flag"><path fill="#4C7BE1" d="M0 0h12v4H0z"/><path fill="#FFD500" d="M0 4h12v3H0z"/><path fill="#E0BC00" d="M0 7h12v1H0z"/></svg>',bi=Bt.extend({options:{position:"bottomright",prefix:'<a href="https://leafletjs.com" title="A JavaScript library for interactive maps">'+(S.inlineSvg?Xo+" ":"")+"Leaflet</a>"},initialize:function(t){w(this,t),this._attributions={}},onAdd:function(t){t.attributionControl=this,this._container=Y("div","leaflet-control-attribution"),ye(this._container);for(var e in t._layers)t._layers[e].getAttribution&&this.addAttribution(t._layers[e].getAttribution());return this._update(),t.on("layeradd",this._addAttribution,this),this._container},onRemove:function(t){t.off("layeradd",this._addAttribution,this)},_addAttribution:function(t){t.layer.getAttribution&&(this.addAttribution(t.layer.getAttribution()),t.layer.once("remove",function(){this.removeAttribution(t.layer.getAttribution())},this))},setPrefix:function(t){return this.options.prefix=t,this._update(),this},addAttribution:function(t){return t?(this._attributions[t]||(this._attributions[t]=0),this._attributions[t]++,this._update(),this):this},removeAttribution:function(t){return t?(this._attributions[t]&&(this._attributions[t]--,this._update()),this):this},_update:function(){if(this._map){var t=[];for(var e in this._attributions)this._attributions[e]&&t.push(e);var i=[];this.options.prefix&&i.push(this.options.prefix),t.length&&i.push(t.join(", ")),this._container.innerHTML=i.join(' <span aria-hidden="true">|</span> ')}}});V.mergeOptions({attributionControl:!0}),V.addInitHook(function(){this.options.attributionControl&&new bi().addTo(this)});var Jo=function(t){return new bi(t)};Bt.Layers=fn,Bt.Zoom=yi,Bt.Scale=mn,Bt.Attribution=bi,be.layers=jo,be.zoom=Ko,be.scale=Yo,be.attribution=Jo;var Zt=Q.extend({initialize:function(t){this._map=t},enable:function(){return this._enabled?this:(this._enabled=!0,this.addHooks(),this)},disable:function(){return this._enabled?(this._enabled=!1,this.removeHooks(),this):this},enabled:function(){return!!this._enabled}});Zt.addTo=function(t,e){return t.addHandler(e,this),this};var Qo={Events:lt},_n=S.touch?"touchstart mousedown":"mousedown",Gt=wt.extend({options:{clickTolerance:3},initialize:function(t,e,i,n){w(this,n),this._element=t,this._dragStartTarget=e||t,this._preventOutline=i},enable:function(){this._enabled||(R(this._dragStartTarget,_n,this._onDown,this),this._enabled=!0)},disable:function(){this._enabled&&(Gt._dragging===this&&this.finishDrag(!0),et(this._dragStartTarget,_n,this._onDown,this),this._enabled=!1,this._moved=!1)},_onDown:function(t){if(this._enabled&&(this._moved=!1,!si(this._element,"leaflet-zoom-anim"))){if(t.touches&&t.touches.length!==1){Gt._dragging===this&&this.finishDrag();return}if(!(Gt._dragging||t.shiftKey||t.which!==1&&t.button!==1&&!t.touches)&&(Gt._dragging=this,this._preventOutline&&ui(this._element),hi(),_e(),!this._moving)){this.fire("down");var e=t.touches?t.touches[0]:t,i=ln(this._element);this._startPoint=new N(e.clientX,e.clientY),this._startPos=Yt(this._element),this._parentScale=pi(i);var n=t.type==="mousedown";R(document,n?"mousemove":"touchmove",this._onMove,this),R(document,n?"mouseup":"touchend touchcancel",this._onUp,this)}}},_onMove:function(t){if(this._enabled){if(t.touches&&t.touches.length>1){this._moved=!0;return}var e=t.touches&&t.touches.length===1?t.touches[0]:t,i=new N(e.clientX,e.clientY)._subtract(this._startPoint);!i.x&&!i.y||Math.abs(i.x)+Math.abs(i.y)<this.options.clickTolerance||(i.x/=this._parentScale.x,i.y/=this._parentScale.y,vt(t),this._moved||(this.fire("dragstart"),this._moved=!0,W(document.body,"leaflet-dragging"),this._lastTarget=t.target||t.srcElement,window.SVGElementInstance&&this._lastTarget instanceof window.SVGElementInstance&&(this._lastTarget=this._lastTarget.correspondingUseElement),W(this._lastTarget,"leaflet-drag-target")),this._newPos=this._startPos.add(i),this._moving=!0,this._lastEvent=t,this._updatePosition())}},_updatePosition:function(){var t={originalEvent:this._lastEvent};this.fire("predrag",t),pt(this._element,this._newPos),this.fire("drag",t)},_onUp:function(){this._enabled&&this.finishDrag()},finishDrag:function(t){ht(document.body,"leaflet-dragging"),this._lastTarget&&(ht(this._lastTarget,"leaflet-drag-target"),this._lastTarget=null),et(document,"mousemove touchmove",this._onMove,this),et(document,"mouseup touchend touchcancel",this._onUp,this),ci(),ge();var e=this._moved&&this._moving;this._moving=!1,Gt._dragging=!1,e&&this.fire("dragend",{noInertia:t,distance:this._newPos.distanceTo(this._startPos)})}});function gn(t,e,i){var n,o=[1,4,2,8],r,c,u,m,v,k,B,$;for(r=0,k=t.length;r<k;r++)t[r]._code=Qt(t[r],e);for(u=0;u<4;u++){for(B=o[u],n=[],r=0,k=t.length,c=k-1;r<k;c=r++)m=t[r],v=t[c],m._code&B?v._code&B||($=Ie(v,m,B,e,i),$._code=Qt($,e),n.push($)):(v._code&B&&($=Ie(v,m,B,e,i),$._code=Qt($,e),n.push($)),n.push(m));t=n}return t}function vn(t,e){var i,n,o,r,c,u,m,v,k;if(!t||t.length===0)throw new Error("latlngs not passed");St(t)||(console.warn("latlngs are not flat! Only the first ring will be used"),t=t[0]);var B=U([0,0]),$=rt(t),bt=$.getNorthWest().distanceTo($.getSouthWest())*$.getNorthEast().distanceTo($.getNorthWest());bt<1700&&(B=xi(t));var mt=t.length,zt=[];for(i=0;i<mt;i++){var xt=U(t[i]);zt.push(e.project(U([xt.lat-B.lat,xt.lng-B.lng])))}for(u=m=v=0,i=0,n=mt-1;i<mt;n=i++)o=zt[i],r=zt[n],c=o.y*r.x-r.y*o.x,m+=(o.x+r.x)*c,v+=(o.y+r.y)*c,u+=c*3;u===0?k=zt[0]:k=[m/u,v/u];var ue=e.unproject(I(k));return U([ue.lat+B.lat,ue.lng+B.lng])}function xi(t){for(var e=0,i=0,n=0,o=0;o<t.length;o++){var r=U(t[o]);e+=r.lat,i+=r.lng,n++}return U([e/n,i/n])}var tr={__proto__:null,clipPolygon:gn,polygonCenter:vn,centroid:xi};function yn(t,e){if(!e||!t.length)return t.slice();var i=e*e;return t=nr(t,i),t=ir(t,i),t}function bn(t,e,i){return Math.sqrt(xe(t,e,i,!0))}function er(t,e,i){return xe(t,e,i)}function ir(t,e){var i=t.length,n=typeof Uint8Array<"u"?Uint8Array:Array,o=new n(i);o[0]=o[i-1]=1,wi(t,o,e,0,i-1);var r,c=[];for(r=0;r<i;r++)o[r]&&c.push(t[r]);return c}function wi(t,e,i,n,o){var r=0,c,u,m;for(u=n+1;u<=o-1;u++)m=xe(t[u],t[n],t[o],!0),m>r&&(c=u,r=m);r>i&&(e[c]=1,wi(t,e,i,n,c),wi(t,e,i,c,o))}function nr(t,e){for(var i=[t[0]],n=1,o=0,r=t.length;n<r;n++)or(t[n],t[o])>e&&(i.push(t[n]),o=n);return o<r-1&&i.push(t[r-1]),i}var xn;function wn(t,e,i,n,o){var r=n?xn:Qt(t,i),c=Qt(e,i),u,m,v;for(xn=c;;){if(!(r|c))return[t,e];if(r&c)return!1;u=r||c,m=Ie(t,e,u,i,o),v=Qt(m,i),u===r?(t=m,r=v):(e=m,c=v)}}function Ie(t,e,i,n,o){var r=e.x-t.x,c=e.y-t.y,u=n.min,m=n.max,v,k;return i&8?(v=t.x+r*(m.y-t.y)/c,k=m.y):i&4?(v=t.x+r*(u.y-t.y)/c,k=u.y):i&2?(v=m.x,k=t.y+c*(m.x-t.x)/r):i&1&&(v=u.x,k=t.y+c*(u.x-t.x)/r),new N(v,k,o)}function Qt(t,e){var i=0;return t.x<e.min.x?i|=1:t.x>e.max.x&&(i|=2),t.y<e.min.y?i|=4:t.y>e.max.y&&(i|=8),i}function or(t,e){var i=e.x-t.x,n=e.y-t.y;return i*i+n*n}function xe(t,e,i,n){var o=e.x,r=e.y,c=i.x-o,u=i.y-r,m=c*c+u*u,v;return m>0&&(v=((t.x-o)*c+(t.y-r)*u)/m,v>1?(o=i.x,r=i.y):v>0&&(o+=c*v,r+=u*v)),c=t.x-o,u=t.y-r,n?c*c+u*u:new N(o,r)}function St(t){return!A(t[0])||typeof t[0][0]!="object"&&typeof t[0][0]<"u"}function kn(t){return console.warn("Deprecated use of _flat, please use L.LineUtil.isFlat instead."),St(t)}function Pn(t,e){var i,n,o,r,c,u,m,v;if(!t||t.length===0)throw new Error("latlngs not passed");St(t)||(console.warn("latlngs are not flat! Only the first ring will be used"),t=t[0]);var k=U([0,0]),B=rt(t),$=B.getNorthWest().distanceTo(B.getSouthWest())*B.getNorthEast().distanceTo(B.getNorthWest());$<1700&&(k=xi(t));var bt=t.length,mt=[];for(i=0;i<bt;i++){var zt=U(t[i]);mt.push(e.project(U([zt.lat-k.lat,zt.lng-k.lng])))}for(i=0,n=0;i<bt-1;i++)n+=mt[i].distanceTo(mt[i+1])/2;if(n===0)v=mt[0];else for(i=0,r=0;i<bt-1;i++)if(c=mt[i],u=mt[i+1],o=c.distanceTo(u),r+=o,r>n){m=(r-n)/o,v=[u.x-m*(u.x-c.x),u.y-m*(u.y-c.y)];break}var xt=e.unproject(I(v));return U([xt.lat+k.lat,xt.lng+k.lng])}var rr={__proto__:null,simplify:yn,pointToSegmentDistance:bn,closestPointOnSegment:er,clipSegment:wn,_getEdgeIntersection:Ie,_getBitCode:Qt,_sqClosestPointOnSegment:xe,isFlat:St,_flat:kn,polylineCenter:Pn},ki={project:function(t){return new N(t.lng,t.lat)},unproject:function(t){return new K(t.y,t.x)},bounds:new it([-180,-90],[180,90])},Pi={R:6378137,R_MINOR:6356752314245179e-9,bounds:new it([-2003750834279e-5,-1549657073972e-5],[2003750834279e-5,1876465623138e-5]),project:function(t){var e=Math.PI/180,i=this.R,n=t.lat*e,o=this.R_MINOR/i,r=Math.sqrt(1-o*o),c=r*Math.sin(n),u=Math.tan(Math.PI/4-n/2)/Math.pow((1-c)/(1+c),r/2);return n=-i*Math.log(Math.max(u,1e-10)),new N(t.lng*e*i,n)},unproject:function(t){for(var e=180/Math.PI,i=this.R,n=this.R_MINOR/i,o=Math.sqrt(1-n*n),r=Math.exp(-t.y/i),c=Math.PI/2-2*Math.atan(r),u=0,m=.1,v;u<15&&Math.abs(m)>1e-7;u++)v=o*Math.sin(c),v=Math.pow((1-v)/(1+v),o/2),m=Math.PI/2-2*Math.atan(r*v)-c,c+=m;return new K(c*e,t.x*e/i)}},sr={__proto__:null,LonLat:ki,Mercator:Pi,SphericalMercator:ot},ar=a({},E,{code:"EPSG:3395",projection:Pi,transformation:(function(){var t=.5/(Math.PI*Pi.R);return tt(t,.5,-t,.5)})()}),Ln=a({},E,{code:"EPSG:4326",projection:ki,transformation:tt(1/180,1,-1/180,.5)}),lr=a({},kt,{projection:ki,transformation:tt(1,0,-1,0),scale:function(t){return Math.pow(2,t)},zoom:function(t){return Math.log(t)/Math.LN2},distance:function(t,e){var i=e.lng-t.lng,n=e.lat-t.lat;return Math.sqrt(i*i+n*n)},infinite:!0});kt.Earth=E,kt.EPSG3395=ar,kt.EPSG3857=ut,kt.EPSG900913=Lt,kt.EPSG4326=Ln,kt.Simple=lr;var Ot=wt.extend({options:{pane:"overlayPane",attribution:null,bubblingMouseEvents:!0},addTo:function(t){return t.addLayer(this),this},remove:function(){return this.removeFrom(this._map||this._mapToAdd)},removeFrom:function(t){return t&&t.removeLayer(this),this},getPane:function(t){return this._map.getPane(t?this.options[t]||t:this.options.pane)},addInteractiveTarget:function(t){return this._map._targets[f(t)]=this,this},removeInteractiveTarget:function(t){return delete this._map._targets[f(t)],this},getAttribution:function(){return this.options.attribution},_layerAdd:function(t){var e=t.target;if(e.hasLayer(this)){if(this._map=e,this._zoomAnimated=e._zoomAnimated,this.getEvents){var i=this.getEvents();e.on(i,this),this.once("remove",function(){e.off(i,this)},this)}this.onAdd(e),this.fire("add"),e.fire("layeradd",{layer:this})}}});V.include({addLayer:function(t){if(!t._layerAdd)throw new Error("The provided object is not a Layer.");var e=f(t);return this._layers[e]?this:(this._layers[e]=t,t._mapToAdd=this,t.beforeAdd&&t.beforeAdd(this),this.whenReady(t._layerAdd,t),this)},removeLayer:function(t){var e=f(t);return this._layers[e]?(this._loaded&&t.onRemove(this),delete this._layers[e],this._loaded&&(this.fire("layerremove",{layer:t}),t.fire("remove")),t._map=t._mapToAdd=null,this):this},hasLayer:function(t){return f(t)in this._layers},eachLayer:function(t,e){for(var i in this._layers)t.call(e,this._layers[i]);return this},_addLayers:function(t){t=t?A(t)?t:[t]:[];for(var e=0,i=t.length;e<i;e++)this.addLayer(t[e])},_addZoomLimit:function(t){(!isNaN(t.options.maxZoom)||!isNaN(t.options.minZoom))&&(this._zoomBoundLayers[f(t)]=t,this._updateZoomLevels())},_removeZoomLimit:function(t){var e=f(t);this._zoomBoundLayers[e]&&(delete this._zoomBoundLayers[e],this._updateZoomLevels())},_updateZoomLevels:function(){var t=1/0,e=-1/0,i=this._getZoomSpan();for(var n in this._zoomBoundLayers){var o=this._zoomBoundLayers[n].options;t=o.minZoom===void 0?t:Math.min(t,o.minZoom),e=o.maxZoom===void 0?e:Math.max(e,o.maxZoom)}this._layersMaxZoom=e===-1/0?void 0:e,this._layersMinZoom=t===1/0?void 0:t,i!==this._getZoomSpan()&&this.fire("zoomlevelschange"),this.options.maxZoom===void 0&&this._layersMaxZoom&&this.getZoom()>this._layersMaxZoom&&this.setZoom(this._layersMaxZoom),this.options.minZoom===void 0&&this._layersMinZoom&&this.getZoom()<this._layersMinZoom&&this.setZoom(this._layersMinZoom)}});var ae=Ot.extend({initialize:function(t,e){w(this,e),this._layers={};var i,n;if(t)for(i=0,n=t.length;i<n;i++)this.addLayer(t[i])},addLayer:function(t){var e=this.getLayerId(t);return this._layers[e]=t,this._map&&this._map.addLayer(t),this},removeLayer:function(t){var e=t in this._layers?t:this.getLayerId(t);return this._map&&this._layers[e]&&this._map.removeLayer(this._layers[e]),delete this._layers[e],this},hasLayer:function(t){var e=typeof t=="number"?t:this.getLayerId(t);return e in this._layers},clearLayers:function(){return this.eachLayer(this.removeLayer,this)},invoke:function(t){var e=Array.prototype.slice.call(arguments,1),i,n;for(i in this._layers)n=this._layers[i],n[t]&&n[t].apply(n,e);return this},onAdd:function(t){this.eachLayer(t.addLayer,t)},onRemove:function(t){this.eachLayer(t.removeLayer,t)},eachLayer:function(t,e){for(var i in this._layers)t.call(e,this._layers[i]);return this},getLayer:function(t){return this._layers[t]},getLayers:function(){var t=[];return this.eachLayer(t.push,t),t},setZIndex:function(t){return this.invoke("setZIndex",t)},getLayerId:function(t){return f(t)}}),hr=function(t,e){return new ae(t,e)},Ht=ae.extend({addLayer:function(t){return this.hasLayer(t)?this:(t.addEventParent(this),ae.prototype.addLayer.call(this,t),this.fire("layeradd",{layer:t}))},removeLayer:function(t){return this.hasLayer(t)?(t in this._layers&&(t=this._layers[t]),t.removeEventParent(this),ae.prototype.removeLayer.call(this,t),this.fire("layerremove",{layer:t})):this},setStyle:function(t){return this.invoke("setStyle",t)},bringToFront:function(){return this.invoke("bringToFront")},bringToBack:function(){return this.invoke("bringToBack")},getBounds:function(){var t=new gt;for(var e in this._layers){var i=this._layers[e];t.extend(i.getBounds?i.getBounds():i.getLatLng())}return t}}),cr=function(t,e){return new Ht(t,e)},le=Q.extend({options:{popupAnchor:[0,0],tooltipAnchor:[0,0],crossOrigin:!1},initialize:function(t){w(this,t)},createIcon:function(t){return this._createIcon("icon",t)},createShadow:function(t){return this._createIcon("shadow",t)},_createIcon:function(t,e){var i=this._getIconUrl(t);if(!i){if(t==="icon")throw new Error("iconUrl not set in Icon options (see the docs).");return null}var n=this._createImg(i,e&&e.tagName==="IMG"?e:null);return this._setIconStyles(n,t),(this.options.crossOrigin||this.options.crossOrigin==="")&&(n.crossOrigin=this.options.crossOrigin===!0?"":this.options.crossOrigin),n},_setIconStyles:function(t,e){var i=this.options,n=i[e+"Size"];typeof n=="number"&&(n=[n,n]);var o=I(n),r=I(e==="shadow"&&i.shadowAnchor||i.iconAnchor||o&&o.divideBy(2,!0));t.className="leaflet-marker-"+e+" "+(i.className||""),r&&(t.style.marginLeft=-r.x+"px",t.style.marginTop=-r.y+"px"),o&&(t.style.width=o.x+"px",t.style.height=o.y+"px")},_createImg:function(t,e){return e=e||document.createElement("img"),e.src=t,e},_getIconUrl:function(t){return S.retina&&this.options[t+"RetinaUrl"]||this.options[t+"Url"]}});function dr(t){return new le(t)}var we=le.extend({options:{iconUrl:"marker-icon.png",iconRetinaUrl:"marker-icon-2x.png",shadowUrl:"marker-shadow.png",iconSize:[25,41],iconAnchor:[12,41],popupAnchor:[1,-34],tooltipAnchor:[16,-28],shadowSize:[41,41]},_getIconUrl:function(t){return typeof we.imagePath!="string"&&(we.imagePath=this._detectIconPath()),(this.options.imagePath||we.imagePath)+le.prototype._getIconUrl.call(this,t)},_stripUrl:function(t){var e=function(i,n,o){var r=n.exec(i);return r&&r[o]};return t=e(t,/^url\((['"])?(.+)\1\)$/,2),t&&e(t,/^(.*)marker-icon\.png$/,1)},_detectIconPath:function(){var t=Y("div","leaflet-default-icon-path",document.body),e=me(t,"background-image")||me(t,"backgroundImage");if(document.body.removeChild(t),e=this._stripUrl(e),e)return e;var i=document.querySelector('link[href$="leaflet.css"]');return i?i.href.substring(0,i.href.length-11-1):""}}),Cn=Zt.extend({initialize:function(t){this._marker=t},addHooks:function(){var t=this._marker._icon;this._draggable||(this._draggable=new Gt(t,t,!0)),this._draggable.on({dragstart:this._onDragStart,predrag:this._onPreDrag,drag:this._onDrag,dragend:this._onDragEnd},this).enable(),W(t,"leaflet-marker-draggable")},removeHooks:function(){this._draggable.off({dragstart:this._onDragStart,predrag:this._onPreDrag,drag:this._onDrag,dragend:this._onDragEnd},this).disable(),this._marker._icon&&ht(this._marker._icon,"leaflet-marker-draggable")},moved:function(){return this._draggable&&this._draggable._moved},_adjustPan:function(t){var e=this._marker,i=e._map,n=this._marker.options.autoPanSpeed,o=this._marker.options.autoPanPadding,r=Yt(e._icon),c=i.getPixelBounds(),u=i.getPixelOrigin(),m=dt(c.min._subtract(u).add(o),c.max._subtract(u).subtract(o));if(!m.contains(r)){var v=I((Math.max(m.max.x,r.x)-m.max.x)/(c.max.x-m.max.x)-(Math.min(m.min.x,r.x)-m.min.x)/(c.min.x-m.min.x),(Math.max(m.max.y,r.y)-m.max.y)/(c.max.y-m.max.y)-(Math.min(m.min.y,r.y)-m.min.y)/(c.min.y-m.min.y)).multiplyBy(n);i.panBy(v,{animate:!1}),this._draggable._newPos._add(v),this._draggable._startPos._add(v),pt(e._icon,this._draggable._newPos),this._onDrag(t),this._panRequest=M(this._adjustPan.bind(this,t))}},_onDragStart:function(){this._oldLatLng=this._marker.getLatLng(),this._marker.closePopup&&this._marker.closePopup(),this._marker.fire("movestart").fire("dragstart")},_onPreDrag:function(t){this._marker.options.autoPan&&(y(this._panRequest),this._panRequest=M(this._adjustPan.bind(this,t)))},_onDrag:function(t){var e=this._marker,i=e._shadow,n=Yt(e._icon),o=e._map.layerPointToLatLng(n);i&&pt(i,n),e._latlng=o,t.latlng=o,t.oldLatLng=this._oldLatLng,e.fire("move",t).fire("drag",t)},_onDragEnd:function(t){y(this._panRequest),delete this._oldLatLng,this._marker.fire("moveend").fire("dragend",t)}}),Ne=Ot.extend({options:{icon:new we,interactive:!0,keyboard:!0,title:"",alt:"Marker",zIndexOffset:0,opacity:1,riseOnHover:!1,riseOffset:250,pane:"markerPane",shadowPane:"shadowPane",bubblingMouseEvents:!1,autoPanOnFocus:!0,draggable:!1,autoPan:!1,autoPanPadding:[50,50],autoPanSpeed:10},initialize:function(t,e){w(this,e),this._latlng=U(t)},onAdd:function(t){this._zoomAnimated=this._zoomAnimated&&t.options.markerZoomAnimation,this._zoomAnimated&&t.on("zoomanim",this._animateZoom,this),this._initIcon(),this.update()},onRemove:function(t){this.dragging&&this.dragging.enabled()&&(this.options.draggable=!0,this.dragging.removeHooks()),delete this.dragging,this._zoomAnimated&&t.off("zoomanim",this._animateZoom,this),this._removeIcon(),this._removeShadow()},getEvents:function(){return{zoom:this.update,viewreset:this.update}},getLatLng:function(){return this._latlng},setLatLng:function(t){var e=this._latlng;return this._latlng=U(t),this.update(),this.fire("move",{oldLatLng:e,latlng:this._latlng})},setZIndexOffset:function(t){return this.options.zIndexOffset=t,this.update()},getIcon:function(){return this.options.icon},setIcon:function(t){return this.options.icon=t,this._map&&(this._initIcon(),this.update()),this._popup&&this.bindPopup(this._popup,this._popup.options),this},getElement:function(){return this._icon},update:function(){if(this._icon&&this._map){var t=this._map.latLngToLayerPoint(this._latlng).round();this._setPos(t)}return this},_initIcon:function(){var t=this.options,e="leaflet-zoom-"+(this._zoomAnimated?"animated":"hide"),i=t.icon.createIcon(this._icon),n=!1;i!==this._icon&&(this._icon&&this._removeIcon(),n=!0,t.title&&(i.title=t.title),i.tagName==="IMG"&&(i.alt=t.alt||"")),W(i,e),t.keyboard&&(i.tabIndex="0",i.setAttribute("role","button")),this._icon=i,t.riseOnHover&&this.on({mouseover:this._bringToFront,mouseout:this._resetZIndex}),this.options.autoPanOnFocus&&R(i,"focus",this._panOnFocus,this);var o=t.icon.createShadow(this._shadow),r=!1;o!==this._shadow&&(this._removeShadow(),r=!0),o&&(W(o,e),o.alt=""),this._shadow=o,t.opacity<1&&this._updateOpacity(),n&&this.getPane().appendChild(this._icon),this._initInteraction(),o&&r&&this.getPane(t.shadowPane).appendChild(this._shadow)},_removeIcon:function(){this.options.riseOnHover&&this.off({mouseover:this._bringToFront,mouseout:this._resetZIndex}),this.options.autoPanOnFocus&&et(this._icon,"focus",this._panOnFocus,this),st(this._icon),this.removeInteractiveTarget(this._icon),this._icon=null},_removeShadow:function(){this._shadow&&st(this._shadow),this._shadow=null},_setPos:function(t){this._icon&&pt(this._icon,t),this._shadow&&pt(this._shadow,t),this._zIndex=t.y+this.options.zIndexOffset,this._resetZIndex()},_updateZIndex:function(t){this._icon&&(this._icon.style.zIndex=this._zIndex+t)},_animateZoom:function(t){var e=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center).round();this._setPos(e)},_initInteraction:function(){if(this.options.interactive&&(W(this._icon,"leaflet-interactive"),this.addInteractiveTarget(this._icon),Cn)){var t=this.options.draggable;this.dragging&&(t=this.dragging.enabled(),this.dragging.disable()),this.dragging=new Cn(this),t&&this.dragging.enable()}},setOpacity:function(t){return this.options.opacity=t,this._map&&this._updateOpacity(),this},_updateOpacity:function(){var t=this.options.opacity;this._icon&&Mt(this._icon,t),this._shadow&&Mt(this._shadow,t)},_bringToFront:function(){this._updateZIndex(this.options.riseOffset)},_resetZIndex:function(){this._updateZIndex(0)},_panOnFocus:function(){var t=this._map;if(t){var e=this.options.icon.options,i=e.iconSize?I(e.iconSize):I(0,0),n=e.iconAnchor?I(e.iconAnchor):I(0,0);t.panInside(this._latlng,{paddingTopLeft:n,paddingBottomRight:i.subtract(n)})}},_getPopupAnchor:function(){return this.options.icon.options.popupAnchor},_getTooltipAnchor:function(){return this.options.icon.options.tooltipAnchor}});function ur(t,e){return new Ne(t,e)}var Vt=Ot.extend({options:{stroke:!0,color:"#3388ff",weight:3,opacity:1,lineCap:"round",lineJoin:"round",dashArray:null,dashOffset:null,fill:!1,fillColor:null,fillOpacity:.2,fillRule:"evenodd",interactive:!0,bubblingMouseEvents:!0},beforeAdd:function(t){this._renderer=t.getRenderer(this)},onAdd:function(){this._renderer._initPath(this),this._reset(),this._renderer._addPath(this)},onRemove:function(){this._renderer._removePath(this)},redraw:function(){return this._map&&this._renderer._updatePath(this),this},setStyle:function(t){return w(this,t),this._renderer&&(this._renderer._updateStyle(this),this.options.stroke&&t&&Object.prototype.hasOwnProperty.call(t,"weight")&&this._updateBounds()),this},bringToFront:function(){return this._renderer&&this._renderer._bringToFront(this),this},bringToBack:function(){return this._renderer&&this._renderer._bringToBack(this),this},getElement:function(){return this._path},_reset:function(){this._project(),this._update()},_clickTolerance:function(){return(this.options.stroke?this.options.weight/2:0)+(this._renderer.options.tolerance||0)}}),Ze=Vt.extend({options:{fill:!0,radius:10},initialize:function(t,e){w(this,e),this._latlng=U(t),this._radius=this.options.radius},setLatLng:function(t){var e=this._latlng;return this._latlng=U(t),this.redraw(),this.fire("move",{oldLatLng:e,latlng:this._latlng})},getLatLng:function(){return this._latlng},setRadius:function(t){return this.options.radius=this._radius=t,this.redraw()},getRadius:function(){return this._radius},setStyle:function(t){var e=t&&t.radius||this._radius;return Vt.prototype.setStyle.call(this,t),this.setRadius(e),this},_project:function(){this._point=this._map.latLngToLayerPoint(this._latlng),this._updateBounds()},_updateBounds:function(){var t=this._radius,e=this._radiusY||t,i=this._clickTolerance(),n=[t+i,e+i];this._pxBounds=new it(this._point.subtract(n),this._point.add(n))},_update:function(){this._map&&this._updatePath()},_updatePath:function(){this._renderer._updateCircle(this)},_empty:function(){return this._radius&&!this._renderer._bounds.intersects(this._pxBounds)},_containsPoint:function(t){return t.distanceTo(this._point)<=this._radius+this._clickTolerance()}});function pr(t,e){return new Ze(t,e)}var Li=Ze.extend({initialize:function(t,e,i){if(typeof e=="number"&&(e=a({},i,{radius:e})),w(this,e),this._latlng=U(t),isNaN(this.options.radius))throw new Error("Circle radius cannot be NaN");this._mRadius=this.options.radius},setRadius:function(t){return this._mRadius=t,this.redraw()},getRadius:function(){return this._mRadius},getBounds:function(){var t=[this._radius,this._radiusY||this._radius];return new gt(this._map.layerPointToLatLng(this._point.subtract(t)),this._map.layerPointToLatLng(this._point.add(t)))},setStyle:Vt.prototype.setStyle,_project:function(){var t=this._latlng.lng,e=this._latlng.lat,i=this._map,n=i.options.crs;if(n.distance===E.distance){var o=Math.PI/180,r=this._mRadius/E.R/o,c=i.project([e+r,t]),u=i.project([e-r,t]),m=c.add(u).divideBy(2),v=i.unproject(m).lat,k=Math.acos((Math.cos(r*o)-Math.sin(e*o)*Math.sin(v*o))/(Math.cos(e*o)*Math.cos(v*o)))/o;(isNaN(k)||k===0)&&(k=r/Math.cos(Math.PI/180*e)),this._point=m.subtract(i.getPixelOrigin()),this._radius=isNaN(k)?0:m.x-i.project([v,t-k]).x,this._radiusY=m.y-c.y}else{var B=n.unproject(n.project(this._latlng).subtract([this._mRadius,0]));this._point=i.latLngToLayerPoint(this._latlng),this._radius=this._point.x-i.latLngToLayerPoint(B).x}this._updateBounds()}});function fr(t,e,i){return new Li(t,e,i)}var Dt=Vt.extend({options:{smoothFactor:1,noClip:!1},initialize:function(t,e){w(this,e),this._setLatLngs(t)},getLatLngs:function(){return this._latlngs},setLatLngs:function(t){return this._setLatLngs(t),this.redraw()},isEmpty:function(){return!this._latlngs.length},closestLayerPoint:function(t){for(var e=1/0,i=null,n=xe,o,r,c=0,u=this._parts.length;c<u;c++)for(var m=this._parts[c],v=1,k=m.length;v<k;v++){o=m[v-1],r=m[v];var B=n(t,o,r,!0);B<e&&(e=B,i=n(t,o,r))}return i&&(i.distance=Math.sqrt(e)),i},getCenter:function(){if(!this._map)throw new Error("Must add layer to map before using getCenter()");return Pn(this._defaultShape(),this._map.options.crs)},getBounds:function(){return this._bounds},addLatLng:function(t,e){return e=e||this._defaultShape(),t=U(t),e.push(t),this._bounds.extend(t),this.redraw()},_setLatLngs:function(t){this._bounds=new gt,this._latlngs=this._convertLatLngs(t)},_defaultShape:function(){return St(this._latlngs)?this._latlngs:this._latlngs[0]},_convertLatLngs:function(t){for(var e=[],i=St(t),n=0,o=t.length;n<o;n++)i?(e[n]=U(t[n]),this._bounds.extend(e[n])):e[n]=this._convertLatLngs(t[n]);return e},_project:function(){var t=new it;this._rings=[],this._projectLatlngs(this._latlngs,this._rings,t),this._bounds.isValid()&&t.isValid()&&(this._rawPxBounds=t,this._updateBounds())},_updateBounds:function(){var t=this._clickTolerance(),e=new N(t,t);this._rawPxBounds&&(this._pxBounds=new it([this._rawPxBounds.min.subtract(e),this._rawPxBounds.max.add(e)]))},_projectLatlngs:function(t,e,i){var n=t[0]instanceof K,o=t.length,r,c;if(n){for(c=[],r=0;r<o;r++)c[r]=this._map.latLngToLayerPoint(t[r]),i.extend(c[r]);e.push(c)}else for(r=0;r<o;r++)this._projectLatlngs(t[r],e,i)},_clipPoints:function(){var t=this._renderer._bounds;if(this._parts=[],!(!this._pxBounds||!this._pxBounds.intersects(t))){if(this.options.noClip){this._parts=this._rings;return}var e=this._parts,i,n,o,r,c,u,m;for(i=0,o=0,r=this._rings.length;i<r;i++)for(m=this._rings[i],n=0,c=m.length;n<c-1;n++)u=wn(m[n],m[n+1],t,n,!0),u&&(e[o]=e[o]||[],e[o].push(u[0]),(u[1]!==m[n+1]||n===c-2)&&(e[o].push(u[1]),o++))}},_simplifyPoints:function(){for(var t=this._parts,e=this.options.smoothFactor,i=0,n=t.length;i<n;i++)t[i]=yn(t[i],e)},_update:function(){this._map&&(this._clipPoints(),this._simplifyPoints(),this._updatePath())},_updatePath:function(){this._renderer._updatePoly(this)},_containsPoint:function(t,e){var i,n,o,r,c,u,m=this._clickTolerance();if(!this._pxBounds||!this._pxBounds.contains(t))return!1;for(i=0,r=this._parts.length;i<r;i++)for(u=this._parts[i],n=0,c=u.length,o=c-1;n<c;o=n++)if(!(!e&&n===0)&&bn(t,u[o],u[n])<=m)return!0;return!1}});function mr(t,e){return new Dt(t,e)}Dt._flat=kn;var he=Dt.extend({options:{fill:!0},isEmpty:function(){return!this._latlngs.length||!this._latlngs[0].length},getCenter:function(){if(!this._map)throw new Error("Must add layer to map before using getCenter()");return vn(this._defaultShape(),this._map.options.crs)},_convertLatLngs:function(t){var e=Dt.prototype._convertLatLngs.call(this,t),i=e.length;return i>=2&&e[0]instanceof K&&e[0].equals(e[i-1])&&e.pop(),e},_setLatLngs:function(t){Dt.prototype._setLatLngs.call(this,t),St(this._latlngs)&&(this._latlngs=[this._latlngs])},_defaultShape:function(){return St(this._latlngs[0])?this._latlngs[0]:this._latlngs[0][0]},_clipPoints:function(){var t=this._renderer._bounds,e=this.options.weight,i=new N(e,e);if(t=new it(t.min.subtract(i),t.max.add(i)),this._parts=[],!(!this._pxBounds||!this._pxBounds.intersects(t))){if(this.options.noClip){this._parts=this._rings;return}for(var n=0,o=this._rings.length,r;n<o;n++)r=gn(this._rings[n],t,!0),r.length&&this._parts.push(r)}},_updatePath:function(){this._renderer._updatePoly(this,!0)},_containsPoint:function(t){var e=!1,i,n,o,r,c,u,m,v;if(!this._pxBounds||!this._pxBounds.contains(t))return!1;for(r=0,m=this._parts.length;r<m;r++)for(i=this._parts[r],c=0,v=i.length,u=v-1;c<v;u=c++)n=i[c],o=i[u],n.y>t.y!=o.y>t.y&&t.x<(o.x-n.x)*(t.y-n.y)/(o.y-n.y)+n.x&&(e=!e);return e||Dt.prototype._containsPoint.call(this,t,!0)}});function _r(t,e){return new he(t,e)}var Ft=Ht.extend({initialize:function(t,e){w(this,e),this._layers={},t&&this.addData(t)},addData:function(t){var e=A(t)?t:t.features,i,n,o;if(e){for(i=0,n=e.length;i<n;i++)o=e[i],(o.geometries||o.geometry||o.features||o.coordinates)&&this.addData(o);return this}var r=this.options;if(r.filter&&!r.filter(t))return this;var c=Re(t,r);return c?(c.feature=Fe(t),c.defaultOptions=c.options,this.resetStyle(c),r.onEachFeature&&r.onEachFeature(t,c),this.addLayer(c)):this},resetStyle:function(t){return t===void 0?this.eachLayer(this.resetStyle,this):(t.options=a({},t.defaultOptions),this._setLayerStyle(t,this.options.style),this)},setStyle:function(t){return this.eachLayer(function(e){this._setLayerStyle(e,t)},this)},_setLayerStyle:function(t,e){t.setStyle&&(typeof e=="function"&&(e=e(t.feature)),t.setStyle(e))}});function Re(t,e){var i=t.type==="Feature"?t.geometry:t,n=i?i.coordinates:null,o=[],r=e&&e.pointToLayer,c=e&&e.coordsToLatLng||Ci,u,m,v,k;if(!n&&!i)return null;switch(i.type){case"Point":return u=c(n),Tn(r,t,u,e);case"MultiPoint":for(v=0,k=n.length;v<k;v++)u=c(n[v]),o.push(Tn(r,t,u,e));return new Ht(o);case"LineString":case"MultiLineString":return m=He(n,i.type==="LineString"?0:1,c),new Dt(m,e);case"Polygon":case"MultiPolygon":return m=He(n,i.type==="Polygon"?1:2,c),new he(m,e);case"GeometryCollection":for(v=0,k=i.geometries.length;v<k;v++){var B=Re({geometry:i.geometries[v],type:"Feature",properties:t.properties},e);B&&o.push(B)}return new Ht(o);case"FeatureCollection":for(v=0,k=i.features.length;v<k;v++){var $=Re(i.features[v],e);$&&o.push($)}return new Ht(o);default:throw new Error("Invalid GeoJSON object.")}}function Tn(t,e,i,n){return t?t(e,i):new Ne(i,n&&n.markersInheritOptions&&n)}function Ci(t){return new K(t[1],t[0],t[2])}function He(t,e,i){for(var n=[],o=0,r=t.length,c;o<r;o++)c=e?He(t[o],e-1,i):(i||Ci)(t[o]),n.push(c);return n}function Ti(t,e){return t=U(t),t.alt!==void 0?[C(t.lng,e),C(t.lat,e),C(t.alt,e)]:[C(t.lng,e),C(t.lat,e)]}function De(t,e,i,n){for(var o=[],r=0,c=t.length;r<c;r++)o.push(e?De(t[r],St(t[r])?0:e-1,i,n):Ti(t[r],n));return!e&&i&&o.length>0&&o.push(o[0].slice()),o}function ce(t,e){return t.feature?a({},t.feature,{geometry:e}):Fe(e)}function Fe(t){return t.type==="Feature"||t.type==="FeatureCollection"?t:{type:"Feature",properties:{},geometry:t}}var Mi={toGeoJSON:function(t){return ce(this,{type:"Point",coordinates:Ti(this.getLatLng(),t)})}};Ne.include(Mi),Li.include(Mi),Ze.include(Mi),Dt.include({toGeoJSON:function(t){var e=!St(this._latlngs),i=De(this._latlngs,e?1:0,!1,t);return ce(this,{type:(e?"Multi":"")+"LineString",coordinates:i})}}),he.include({toGeoJSON:function(t){var e=!St(this._latlngs),i=e&&!St(this._latlngs[0]),n=De(this._latlngs,i?2:e?1:0,!0,t);return e||(n=[n]),ce(this,{type:(i?"Multi":"")+"Polygon",coordinates:n})}}),ae.include({toMultiPoint:function(t){var e=[];return this.eachLayer(function(i){e.push(i.toGeoJSON(t).geometry.coordinates)}),ce(this,{type:"MultiPoint",coordinates:e})},toGeoJSON:function(t){var e=this.feature&&this.feature.geometry&&this.feature.geometry.type;if(e==="MultiPoint")return this.toMultiPoint(t);var i=e==="GeometryCollection",n=[];return this.eachLayer(function(o){if(o.toGeoJSON){var r=o.toGeoJSON(t);if(i)n.push(r.geometry);else{var c=Fe(r);c.type==="FeatureCollection"?n.push.apply(n,c.features):n.push(c)}}}),i?ce(this,{geometries:n,type:"GeometryCollection"}):{type:"FeatureCollection",features:n}}});function Mn(t,e){return new Ft(t,e)}var gr=Mn,We=Ot.extend({options:{opacity:1,alt:"",interactive:!1,crossOrigin:!1,errorOverlayUrl:"",zIndex:1,className:""},initialize:function(t,e,i){this._url=t,this._bounds=rt(e),w(this,i)},onAdd:function(){this._image||(this._initImage(),this.options.opacity<1&&this._updateOpacity()),this.options.interactive&&(W(this._image,"leaflet-interactive"),this.addInteractiveTarget(this._image)),this.getPane().appendChild(this._image),this._reset()},onRemove:function(){st(this._image),this.options.interactive&&this.removeInteractiveTarget(this._image)},setOpacity:function(t){return this.options.opacity=t,this._image&&this._updateOpacity(),this},setStyle:function(t){return t.opacity&&this.setOpacity(t.opacity),this},bringToFront:function(){return this._map&&re(this._image),this},bringToBack:function(){return this._map&&se(this._image),this},setUrl:function(t){return this._url=t,this._image&&(this._image.src=t),this},setBounds:function(t){return this._bounds=rt(t),this._map&&this._reset(),this},getEvents:function(){var t={zoom:this._reset,viewreset:this._reset};return this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},setZIndex:function(t){return this.options.zIndex=t,this._updateZIndex(),this},getBounds:function(){return this._bounds},getElement:function(){return this._image},_initImage:function(){var t=this._url.tagName==="IMG",e=this._image=t?this._url:Y("img");if(W(e,"leaflet-image-layer"),this._zoomAnimated&&W(e,"leaflet-zoom-animated"),this.options.className&&W(e,this.options.className),e.onselectstart=_,e.onmousemove=_,e.onload=p(this.fire,this,"load"),e.onerror=p(this._overlayOnError,this,"error"),(this.options.crossOrigin||this.options.crossOrigin==="")&&(e.crossOrigin=this.options.crossOrigin===!0?"":this.options.crossOrigin),this.options.zIndex&&this._updateZIndex(),t){this._url=e.src;return}e.src=this._url,e.alt=this.options.alt},_animateZoom:function(t){var e=this._map.getZoomScale(t.zoom),i=this._map._latLngBoundsToNewLayerBounds(this._bounds,t.zoom,t.center).min;Kt(this._image,i,e)},_reset:function(){var t=this._image,e=new it(this._map.latLngToLayerPoint(this._bounds.getNorthWest()),this._map.latLngToLayerPoint(this._bounds.getSouthEast())),i=e.getSize();pt(t,e.min),t.style.width=i.x+"px",t.style.height=i.y+"px"},_updateOpacity:function(){Mt(this._image,this.options.opacity)},_updateZIndex:function(){this._image&&this.options.zIndex!==void 0&&this.options.zIndex!==null&&(this._image.style.zIndex=this.options.zIndex)},_overlayOnError:function(){this.fire("error");var t=this.options.errorOverlayUrl;t&&this._url!==t&&(this._url=t,this._image.src=t)},getCenter:function(){return this._bounds.getCenter()}}),vr=function(t,e,i){return new We(t,e,i)},Sn=We.extend({options:{autoplay:!0,loop:!0,keepAspectRatio:!0,muted:!1,playsInline:!0},_initImage:function(){var t=this._url.tagName==="VIDEO",e=this._image=t?this._url:Y("video");if(W(e,"leaflet-image-layer"),this._zoomAnimated&&W(e,"leaflet-zoom-animated"),this.options.className&&W(e,this.options.className),e.onselectstart=_,e.onmousemove=_,e.onloadeddata=p(this.fire,this,"load"),t){for(var i=e.getElementsByTagName("source"),n=[],o=0;o<i.length;o++)n.push(i[o].src);this._url=i.length>0?n:[e.src];return}A(this._url)||(this._url=[this._url]),!this.options.keepAspectRatio&&Object.prototype.hasOwnProperty.call(e.style,"objectFit")&&(e.style.objectFit="fill"),e.autoplay=!!this.options.autoplay,e.loop=!!this.options.loop,e.muted=!!this.options.muted,e.playsInline=!!this.options.playsInline;for(var r=0;r<this._url.length;r++){var c=Y("source");c.src=this._url[r],e.appendChild(c)}}});function yr(t,e,i){return new Sn(t,e,i)}var zn=We.extend({_initImage:function(){var t=this._image=this._url;W(t,"leaflet-image-layer"),this._zoomAnimated&&W(t,"leaflet-zoom-animated"),this.options.className&&W(t,this.options.className),t.onselectstart=_,t.onmousemove=_}});function br(t,e,i){return new zn(t,e,i)}var Rt=Ot.extend({options:{interactive:!1,offset:[0,0],className:"",pane:void 0,content:""},initialize:function(t,e){t&&(t instanceof K||A(t))?(this._latlng=U(t),w(this,e)):(w(this,t),this._source=e),this.options.content&&(this._content=this.options.content)},openOn:function(t){return t=arguments.length?t:this._source._map,t.hasLayer(this)||t.addLayer(this),this},close:function(){return this._map&&this._map.removeLayer(this),this},toggle:function(t){return this._map?this.close():(arguments.length?this._source=t:t=this._source,this._prepareOpen(),this.openOn(t._map)),this},onAdd:function(t){this._zoomAnimated=t._zoomAnimated,this._container||this._initLayout(),t._fadeAnimated&&Mt(this._container,0),clearTimeout(this._removeTimeout),this.getPane().appendChild(this._container),this.update(),t._fadeAnimated&&Mt(this._container,1),this.bringToFront(),this.options.interactive&&(W(this._container,"leaflet-interactive"),this.addInteractiveTarget(this._container))},onRemove:function(t){t._fadeAnimated?(Mt(this._container,0),this._removeTimeout=setTimeout(p(st,void 0,this._container),200)):st(this._container),this.options.interactive&&(ht(this._container,"leaflet-interactive"),this.removeInteractiveTarget(this._container))},getLatLng:function(){return this._latlng},setLatLng:function(t){return this._latlng=U(t),this._map&&(this._updatePosition(),this._adjustPan()),this},getContent:function(){return this._content},setContent:function(t){return this._content=t,this.update(),this},getElement:function(){return this._container},update:function(){this._map&&(this._container.style.visibility="hidden",this._updateContent(),this._updateLayout(),this._updatePosition(),this._container.style.visibility="",this._adjustPan())},getEvents:function(){var t={zoom:this._updatePosition,viewreset:this._updatePosition};return this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},isOpen:function(){return!!this._map&&this._map.hasLayer(this)},bringToFront:function(){return this._map&&re(this._container),this},bringToBack:function(){return this._map&&se(this._container),this},_prepareOpen:function(t){var e=this._source;if(!e._map)return!1;if(e instanceof Ht){e=null;var i=this._source._layers;for(var n in i)if(i[n]._map){e=i[n];break}if(!e)return!1;this._source=e}if(!t)if(e.getCenter)t=e.getCenter();else if(e.getLatLng)t=e.getLatLng();else if(e.getBounds)t=e.getBounds().getCenter();else throw new Error("Unable to get source layer LatLng.");return this.setLatLng(t),this._map&&this.update(),!0},_updateContent:function(){if(this._content){var t=this._contentNode,e=typeof this._content=="function"?this._content(this._source||this):this._content;if(typeof e=="string")t.innerHTML=e;else{for(;t.hasChildNodes();)t.removeChild(t.firstChild);t.appendChild(e)}this.fire("contentupdate")}},_updatePosition:function(){if(this._map){var t=this._map.latLngToLayerPoint(this._latlng),e=I(this.options.offset),i=this._getAnchor();this._zoomAnimated?pt(this._container,t.add(i)):e=e.add(t).add(i);var n=this._containerBottom=-e.y,o=this._containerLeft=-Math.round(this._containerWidth/2)+e.x;this._container.style.bottom=n+"px",this._container.style.left=o+"px"}},_getAnchor:function(){return[0,0]}});V.include({_initOverlay:function(t,e,i,n){var o=e;return o instanceof t||(o=new t(n).setContent(e)),i&&o.setLatLng(i),o}}),Ot.include({_initOverlay:function(t,e,i,n){var o=i;return o instanceof t?(w(o,n),o._source=this):(o=e&&!n?e:new t(n,this),o.setContent(i)),o}});var qe=Rt.extend({options:{pane:"popupPane",offset:[0,7],maxWidth:300,minWidth:50,maxHeight:null,autoPan:!0,autoPanPaddingTopLeft:null,autoPanPaddingBottomRight:null,autoPanPadding:[5,5],keepInView:!1,closeButton:!0,autoClose:!0,closeOnEscapeKey:!0,className:""},openOn:function(t){return t=arguments.length?t:this._source._map,!t.hasLayer(this)&&t._popup&&t._popup.options.autoClose&&t.removeLayer(t._popup),t._popup=this,Rt.prototype.openOn.call(this,t)},onAdd:function(t){Rt.prototype.onAdd.call(this,t),t.fire("popupopen",{popup:this}),this._source&&(this._source.fire("popupopen",{popup:this},!0),this._source instanceof Vt||this._source.on("preclick",Xt))},onRemove:function(t){Rt.prototype.onRemove.call(this,t),t.fire("popupclose",{popup:this}),this._source&&(this._source.fire("popupclose",{popup:this},!0),this._source instanceof Vt||this._source.off("preclick",Xt))},getEvents:function(){var t=Rt.prototype.getEvents.call(this);return(this.options.closeOnClick!==void 0?this.options.closeOnClick:this._map.options.closePopupOnClick)&&(t.preclick=this.close),this.options.keepInView&&(t.moveend=this._adjustPan),t},_initLayout:function(){var t="leaflet-popup",e=this._container=Y("div",t+" "+(this.options.className||"")+" leaflet-zoom-animated"),i=this._wrapper=Y("div",t+"-content-wrapper",e);if(this._contentNode=Y("div",t+"-content",i),ye(e),gi(this._contentNode),R(e,"contextmenu",Xt),this._tipContainer=Y("div",t+"-tip-container",e),this._tip=Y("div",t+"-tip",this._tipContainer),this.options.closeButton){var n=this._closeButton=Y("a",t+"-close-button",e);n.setAttribute("role","button"),n.setAttribute("aria-label","Close popup"),n.href="#close",n.innerHTML='<span aria-hidden="true">&#215;</span>',R(n,"click",function(o){vt(o),this.close()},this)}},_updateLayout:function(){var t=this._contentNode,e=t.style;e.width="",e.whiteSpace="nowrap";var i=t.offsetWidth;i=Math.min(i,this.options.maxWidth),i=Math.max(i,this.options.minWidth),e.width=i+1+"px",e.whiteSpace="",e.height="";var n=t.offsetHeight,o=this.options.maxHeight,r="leaflet-popup-scrolled";o&&n>o?(e.height=o+"px",W(t,r)):ht(t,r),this._containerWidth=this._container.offsetWidth},_animateZoom:function(t){var e=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center),i=this._getAnchor();pt(this._container,e.add(i))},_adjustPan:function(){if(this.options.autoPan){if(this._map._panAnim&&this._map._panAnim.stop(),this._autopanning){this._autopanning=!1;return}var t=this._map,e=parseInt(me(this._container,"marginBottom"),10)||0,i=this._container.offsetHeight+e,n=this._containerWidth,o=new N(this._containerLeft,-i-this._containerBottom);o._add(Yt(this._container));var r=t.layerPointToContainerPoint(o),c=I(this.options.autoPanPadding),u=I(this.options.autoPanPaddingTopLeft||c),m=I(this.options.autoPanPaddingBottomRight||c),v=t.getSize(),k=0,B=0;r.x+n+m.x>v.x&&(k=r.x+n-v.x+m.x),r.x-k-u.x<0&&(k=r.x-u.x),r.y+i+m.y>v.y&&(B=r.y+i-v.y+m.y),r.y-B-u.y<0&&(B=r.y-u.y),(k||B)&&(this.options.keepInView&&(this._autopanning=!0),t.fire("autopanstart").panBy([k,B]))}},_getAnchor:function(){return I(this._source&&this._source._getPopupAnchor?this._source._getPopupAnchor():[0,0])}}),xr=function(t,e){return new qe(t,e)};V.mergeOptions({closePopupOnClick:!0}),V.include({openPopup:function(t,e,i){return this._initOverlay(qe,t,e,i).openOn(this),this},closePopup:function(t){return t=arguments.length?t:this._popup,t&&t.close(),this}}),Ot.include({bindPopup:function(t,e){return this._popup=this._initOverlay(qe,this._popup,t,e),this._popupHandlersAdded||(this.on({click:this._openPopup,keypress:this._onKeyPress,remove:this.closePopup,move:this._movePopup}),this._popupHandlersAdded=!0),this},unbindPopup:function(){return this._popup&&(this.off({click:this._openPopup,keypress:this._onKeyPress,remove:this.closePopup,move:this._movePopup}),this._popupHandlersAdded=!1,this._popup=null),this},openPopup:function(t){return this._popup&&(this instanceof Ht||(this._popup._source=this),this._popup._prepareOpen(t||this._latlng)&&this._popup.openOn(this._map)),this},closePopup:function(){return this._popup&&this._popup.close(),this},togglePopup:function(){return this._popup&&this._popup.toggle(this),this},isPopupOpen:function(){return this._popup?this._popup.isOpen():!1},setPopupContent:function(t){return this._popup&&this._popup.setContent(t),this},getPopup:function(){return this._popup},_openPopup:function(t){if(!(!this._popup||!this._map)){Jt(t);var e=t.layer||t.target;if(this._popup._source===e&&!(e instanceof Vt)){this._map.hasLayer(this._popup)?this.closePopup():this.openPopup(t.latlng);return}this._popup._source=e,this.openPopup(t.latlng)}},_movePopup:function(t){this._popup.setLatLng(t.latlng)},_onKeyPress:function(t){t.originalEvent.keyCode===13&&this._openPopup(t)}});var Ue=Rt.extend({options:{pane:"tooltipPane",offset:[0,0],direction:"auto",permanent:!1,sticky:!1,opacity:.9},onAdd:function(t){Rt.prototype.onAdd.call(this,t),this.setOpacity(this.options.opacity),t.fire("tooltipopen",{tooltip:this}),this._source&&(this.addEventParent(this._source),this._source.fire("tooltipopen",{tooltip:this},!0))},onRemove:function(t){Rt.prototype.onRemove.call(this,t),t.fire("tooltipclose",{tooltip:this}),this._source&&(this.removeEventParent(this._source),this._source.fire("tooltipclose",{tooltip:this},!0))},getEvents:function(){var t=Rt.prototype.getEvents.call(this);return this.options.permanent||(t.preclick=this.close),t},_initLayout:function(){var t="leaflet-tooltip",e=t+" "+(this.options.className||"")+" leaflet-zoom-"+(this._zoomAnimated?"animated":"hide");this._contentNode=this._container=Y("div",e),this._container.setAttribute("role","tooltip"),this._container.setAttribute("id","leaflet-tooltip-"+f(this))},_updateLayout:function(){},_adjustPan:function(){},_setPosition:function(t){var e,i,n=this._map,o=this._container,r=n.latLngToContainerPoint(n.getCenter()),c=n.layerPointToContainerPoint(t),u=this.options.direction,m=o.offsetWidth,v=o.offsetHeight,k=I(this.options.offset),B=this._getAnchor();u==="top"?(e=m/2,i=v):u==="bottom"?(e=m/2,i=0):u==="center"?(e=m/2,i=v/2):u==="right"?(e=0,i=v/2):u==="left"?(e=m,i=v/2):c.x<r.x?(u="right",e=0,i=v/2):(u="left",e=m+(k.x+B.x)*2,i=v/2),t=t.subtract(I(e,i,!0)).add(k).add(B),ht(o,"leaflet-tooltip-right"),ht(o,"leaflet-tooltip-left"),ht(o,"leaflet-tooltip-top"),ht(o,"leaflet-tooltip-bottom"),W(o,"leaflet-tooltip-"+u),pt(o,t)},_updatePosition:function(){var t=this._map.latLngToLayerPoint(this._latlng);this._setPosition(t)},setOpacity:function(t){this.options.opacity=t,this._container&&Mt(this._container,t)},_animateZoom:function(t){var e=this._map._latLngToNewLayerPoint(this._latlng,t.zoom,t.center);this._setPosition(e)},_getAnchor:function(){return I(this._source&&this._source._getTooltipAnchor&&!this.options.sticky?this._source._getTooltipAnchor():[0,0])}}),wr=function(t,e){return new Ue(t,e)};V.include({openTooltip:function(t,e,i){return this._initOverlay(Ue,t,e,i).openOn(this),this},closeTooltip:function(t){return t.close(),this}}),Ot.include({bindTooltip:function(t,e){return this._tooltip&&this.isTooltipOpen()&&this.unbindTooltip(),this._tooltip=this._initOverlay(Ue,this._tooltip,t,e),this._initTooltipInteractions(),this._tooltip.options.permanent&&this._map&&this._map.hasLayer(this)&&this.openTooltip(),this},unbindTooltip:function(){return this._tooltip&&(this._initTooltipInteractions(!0),this.closeTooltip(),this._tooltip=null),this},_initTooltipInteractions:function(t){if(!(!t&&this._tooltipHandlersAdded)){var e=t?"off":"on",i={remove:this.closeTooltip,move:this._moveTooltip};this._tooltip.options.permanent?i.add=this._openTooltip:(i.mouseover=this._openTooltip,i.mouseout=this.closeTooltip,i.click=this._openTooltip,this._map?this._addFocusListeners():i.add=this._addFocusListeners),this._tooltip.options.sticky&&(i.mousemove=this._moveTooltip),this[e](i),this._tooltipHandlersAdded=!t}},openTooltip:function(t){return this._tooltip&&(this instanceof Ht||(this._tooltip._source=this),this._tooltip._prepareOpen(t)&&(this._tooltip.openOn(this._map),this.getElement?this._setAriaDescribedByOnLayer(this):this.eachLayer&&this.eachLayer(this._setAriaDescribedByOnLayer,this))),this},closeTooltip:function(){if(this._tooltip)return this._tooltip.close()},toggleTooltip:function(){return this._tooltip&&this._tooltip.toggle(this),this},isTooltipOpen:function(){return this._tooltip.isOpen()},setTooltipContent:function(t){return this._tooltip&&this._tooltip.setContent(t),this},getTooltip:function(){return this._tooltip},_addFocusListeners:function(){this.getElement?this._addFocusListenersOnLayer(this):this.eachLayer&&this.eachLayer(this._addFocusListenersOnLayer,this)},_addFocusListenersOnLayer:function(t){var e=typeof t.getElement=="function"&&t.getElement();e&&(R(e,"focus",function(){this._tooltip._source=t,this.openTooltip()},this),R(e,"blur",this.closeTooltip,this))},_setAriaDescribedByOnLayer:function(t){var e=typeof t.getElement=="function"&&t.getElement();e&&e.setAttribute("aria-describedby",this._tooltip._container.id)},_openTooltip:function(t){if(!(!this._tooltip||!this._map)){if(this._map.dragging&&this._map.dragging.moving()&&!this._openOnceFlag){this._openOnceFlag=!0;var e=this;this._map.once("moveend",function(){e._openOnceFlag=!1,e._openTooltip(t)});return}this._tooltip._source=t.layer||t.target,this.openTooltip(this._tooltip.options.sticky?t.latlng:void 0)}},_moveTooltip:function(t){var e=t.latlng,i,n;this._tooltip.options.sticky&&t.originalEvent&&(i=this._map.mouseEventToContainerPoint(t.originalEvent),n=this._map.containerPointToLayerPoint(i),e=this._map.layerPointToLatLng(n)),this._tooltip.setLatLng(e)}});var An=le.extend({options:{iconSize:[12,12],html:!1,bgPos:null,className:"leaflet-div-icon"},createIcon:function(t){var e=t&&t.tagName==="DIV"?t:document.createElement("div"),i=this.options;if(i.html instanceof Element?(ze(e),e.appendChild(i.html)):e.innerHTML=i.html!==!1?i.html:"",i.bgPos){var n=I(i.bgPos);e.style.backgroundPosition=-n.x+"px "+-n.y+"px"}return this._setIconStyles(e,"icon"),e},createShadow:function(){return null}});function kr(t){return new An(t)}le.Default=we;var ke=Ot.extend({options:{tileSize:256,opacity:1,updateWhenIdle:S.mobile,updateWhenZooming:!0,updateInterval:200,zIndex:1,bounds:null,minZoom:0,maxZoom:void 0,maxNativeZoom:void 0,minNativeZoom:void 0,noWrap:!1,pane:"tilePane",className:"",keepBuffer:2},initialize:function(t){w(this,t)},onAdd:function(){this._initContainer(),this._levels={},this._tiles={},this._resetView()},beforeAdd:function(t){t._addZoomLimit(this)},onRemove:function(t){this._removeAllTiles(),st(this._container),t._removeZoomLimit(this),this._container=null,this._tileZoom=void 0},bringToFront:function(){return this._map&&(re(this._container),this._setAutoZIndex(Math.max)),this},bringToBack:function(){return this._map&&(se(this._container),this._setAutoZIndex(Math.min)),this},getContainer:function(){return this._container},setOpacity:function(t){return this.options.opacity=t,this._updateOpacity(),this},setZIndex:function(t){return this.options.zIndex=t,this._updateZIndex(),this},isLoading:function(){return this._loading},redraw:function(){if(this._map){this._removeAllTiles();var t=this._clampZoom(this._map.getZoom());t!==this._tileZoom&&(this._tileZoom=t,this._updateLevels()),this._update()}return this},getEvents:function(){var t={viewprereset:this._invalidateAll,viewreset:this._resetView,zoom:this._resetView,moveend:this._onMoveEnd};return this.options.updateWhenIdle||(this._onMove||(this._onMove=g(this._onMoveEnd,this.options.updateInterval,this)),t.move=this._onMove),this._zoomAnimated&&(t.zoomanim=this._animateZoom),t},createTile:function(){return document.createElement("div")},getTileSize:function(){var t=this.options.tileSize;return t instanceof N?t:new N(t,t)},_updateZIndex:function(){this._container&&this.options.zIndex!==void 0&&this.options.zIndex!==null&&(this._container.style.zIndex=this.options.zIndex)},_setAutoZIndex:function(t){for(var e=this.getPane().children,i=-t(-1/0,1/0),n=0,o=e.length,r;n<o;n++)r=e[n].style.zIndex,e[n]!==this._container&&r&&(i=t(i,+r));isFinite(i)&&(this.options.zIndex=i+t(-1,1),this._updateZIndex())},_updateOpacity:function(){if(this._map&&!S.ielt9){Mt(this._container,this.options.opacity);var t=+new Date,e=!1,i=!1;for(var n in this._tiles){var o=this._tiles[n];if(!(!o.current||!o.loaded)){var r=Math.min(1,(t-o.loaded)/200);Mt(o.el,r),r<1?e=!0:(o.active?i=!0:this._onOpaqueTile(o),o.active=!0)}}i&&!this._noPrune&&this._pruneTiles(),e&&(y(this._fadeFrame),this._fadeFrame=M(this._updateOpacity,this))}},_onOpaqueTile:_,_initContainer:function(){this._container||(this._container=Y("div","leaflet-layer "+(this.options.className||"")),this._updateZIndex(),this.options.opacity<1&&this._updateOpacity(),this.getPane().appendChild(this._container))},_updateLevels:function(){var t=this._tileZoom,e=this.options.maxZoom;if(t!==void 0){for(var i in this._levels)i=Number(i),this._levels[i].el.children.length||i===t?(this._levels[i].el.style.zIndex=e-Math.abs(t-i),this._onUpdateLevel(i)):(st(this._levels[i].el),this._removeTilesAtZoom(i),this._onRemoveLevel(i),delete this._levels[i]);var n=this._levels[t],o=this._map;return n||(n=this._levels[t]={},n.el=Y("div","leaflet-tile-container leaflet-zoom-animated",this._container),n.el.style.zIndex=e,n.origin=o.project(o.unproject(o.getPixelOrigin()),t).round(),n.zoom=t,this._setZoomTransform(n,o.getCenter(),o.getZoom()),_(n.el.offsetWidth),this._onCreateLevel(n)),this._level=n,n}},_onUpdateLevel:_,_onRemoveLevel:_,_onCreateLevel:_,_pruneTiles:function(){if(this._map){var t,e,i=this._map.getZoom();if(i>this.options.maxZoom||i<this.options.minZoom){this._removeAllTiles();return}for(t in this._tiles)e=this._tiles[t],e.retain=e.current;for(t in this._tiles)if(e=this._tiles[t],e.current&&!e.active){var n=e.coords;this._retainParent(n.x,n.y,n.z,n.z-5)||this._retainChildren(n.x,n.y,n.z,n.z+2)}for(t in this._tiles)this._tiles[t].retain||this._removeTile(t)}},_removeTilesAtZoom:function(t){for(var e in this._tiles)this._tiles[e].coords.z===t&&this._removeTile(e)},_removeAllTiles:function(){for(var t in this._tiles)this._removeTile(t)},_invalidateAll:function(){for(var t in this._levels)st(this._levels[t].el),this._onRemoveLevel(Number(t)),delete this._levels[t];this._removeAllTiles(),this._tileZoom=void 0},_retainParent:function(t,e,i,n){var o=Math.floor(t/2),r=Math.floor(e/2),c=i-1,u=new N(+o,+r);u.z=+c;var m=this._tileCoordsToKey(u),v=this._tiles[m];return v&&v.active?(v.retain=!0,!0):(v&&v.loaded&&(v.retain=!0),c>n?this._retainParent(o,r,c,n):!1)},_retainChildren:function(t,e,i,n){for(var o=2*t;o<2*t+2;o++)for(var r=2*e;r<2*e+2;r++){var c=new N(o,r);c.z=i+1;var u=this._tileCoordsToKey(c),m=this._tiles[u];if(m&&m.active){m.retain=!0;continue}else m&&m.loaded&&(m.retain=!0);i+1<n&&this._retainChildren(o,r,i+1,n)}},_resetView:function(t){var e=t&&(t.pinch||t.flyTo);this._setView(this._map.getCenter(),this._map.getZoom(),e,e)},_animateZoom:function(t){this._setView(t.center,t.zoom,!0,t.noUpdate)},_clampZoom:function(t){var e=this.options;return e.minNativeZoom!==void 0&&t<e.minNativeZoom?e.minNativeZoom:e.maxNativeZoom!==void 0&&e.maxNativeZoom<t?e.maxNativeZoom:t},_setView:function(t,e,i,n){var o=Math.round(e);this.options.maxZoom!==void 0&&o>this.options.maxZoom||this.options.minZoom!==void 0&&o<this.options.minZoom?o=void 0:o=this._clampZoom(o);var r=this.options.updateWhenZooming&&o!==this._tileZoom;(!n||r)&&(this._tileZoom=o,this._abortLoading&&this._abortLoading(),this._updateLevels(),this._resetGrid(),o!==void 0&&this._update(t),i||this._pruneTiles(),this._noPrune=!!i),this._setZoomTransforms(t,e)},_setZoomTransforms:function(t,e){for(var i in this._levels)this._setZoomTransform(this._levels[i],t,e)},_setZoomTransform:function(t,e,i){var n=this._map.getZoomScale(i,t.zoom),o=t.origin.multiplyBy(n).subtract(this._map._getNewPixelOrigin(e,i)).round();S.any3d?Kt(t.el,o,n):pt(t.el,o)},_resetGrid:function(){var t=this._map,e=t.options.crs,i=this._tileSize=this.getTileSize(),n=this._tileZoom,o=this._map.getPixelWorldBounds(this._tileZoom);o&&(this._globalTileRange=this._pxBoundsToTileRange(o)),this._wrapX=e.wrapLng&&!this.options.noWrap&&[Math.floor(t.project([0,e.wrapLng[0]],n).x/i.x),Math.ceil(t.project([0,e.wrapLng[1]],n).x/i.y)],this._wrapY=e.wrapLat&&!this.options.noWrap&&[Math.floor(t.project([e.wrapLat[0],0],n).y/i.x),Math.ceil(t.project([e.wrapLat[1],0],n).y/i.y)]},_onMoveEnd:function(){!this._map||this._map._animatingZoom||this._update()},_getTiledPixelBounds:function(t){var e=this._map,i=e._animatingZoom?Math.max(e._animateToZoom,e.getZoom()):e.getZoom(),n=e.getZoomScale(i,this._tileZoom),o=e.project(t,this._tileZoom).floor(),r=e.getSize().divideBy(n*2);return new it(o.subtract(r),o.add(r))},_update:function(t){var e=this._map;if(e){var i=this._clampZoom(e.getZoom());if(t===void 0&&(t=e.getCenter()),this._tileZoom!==void 0){var n=this._getTiledPixelBounds(t),o=this._pxBoundsToTileRange(n),r=o.getCenter(),c=[],u=this.options.keepBuffer,m=new it(o.getBottomLeft().subtract([u,-u]),o.getTopRight().add([u,-u]));if(!(isFinite(o.min.x)&&isFinite(o.min.y)&&isFinite(o.max.x)&&isFinite(o.max.y)))throw new Error("Attempted to load an infinite number of tiles");for(var v in this._tiles){var k=this._tiles[v].coords;(k.z!==this._tileZoom||!m.contains(new N(k.x,k.y)))&&(this._tiles[v].current=!1)}if(Math.abs(i-this._tileZoom)>1){this._setView(t,i);return}for(var B=o.min.y;B<=o.max.y;B++)for(var $=o.min.x;$<=o.max.x;$++){var bt=new N($,B);if(bt.z=this._tileZoom,!!this._isValidTile(bt)){var mt=this._tiles[this._tileCoordsToKey(bt)];mt?mt.current=!0:c.push(bt)}}if(c.sort(function(xt,ue){return xt.distanceTo(r)-ue.distanceTo(r)}),c.length!==0){this._loading||(this._loading=!0,this.fire("loading"));var zt=document.createDocumentFragment();for($=0;$<c.length;$++)this._addTile(c[$],zt);this._level.el.appendChild(zt)}}}},_isValidTile:function(t){var e=this._map.options.crs;if(!e.infinite){var i=this._globalTileRange;if(!e.wrapLng&&(t.x<i.min.x||t.x>i.max.x)||!e.wrapLat&&(t.y<i.min.y||t.y>i.max.y))return!1}if(!this.options.bounds)return!0;var n=this._tileCoordsToBounds(t);return rt(this.options.bounds).overlaps(n)},_keyToBounds:function(t){return this._tileCoordsToBounds(this._keyToTileCoords(t))},_tileCoordsToNwSe:function(t){var e=this._map,i=this.getTileSize(),n=t.scaleBy(i),o=n.add(i),r=e.unproject(n,t.z),c=e.unproject(o,t.z);return[r,c]},_tileCoordsToBounds:function(t){var e=this._tileCoordsToNwSe(t),i=new gt(e[0],e[1]);return this.options.noWrap||(i=this._map.wrapLatLngBounds(i)),i},_tileCoordsToKey:function(t){return t.x+":"+t.y+":"+t.z},_keyToTileCoords:function(t){var e=t.split(":"),i=new N(+e[0],+e[1]);return i.z=+e[2],i},_removeTile:function(t){var e=this._tiles[t];e&&(st(e.el),delete this._tiles[t],this.fire("tileunload",{tile:e.el,coords:this._keyToTileCoords(t)}))},_initTile:function(t){W(t,"leaflet-tile");var e=this.getTileSize();t.style.width=e.x+"px",t.style.height=e.y+"px",t.onselectstart=_,t.onmousemove=_,S.ielt9&&this.options.opacity<1&&Mt(t,this.options.opacity)},_addTile:function(t,e){var i=this._getTilePos(t),n=this._tileCoordsToKey(t),o=this.createTile(this._wrapCoords(t),p(this._tileReady,this,t));this._initTile(o),this.createTile.length<2&&M(p(this._tileReady,this,t,null,o)),pt(o,i),this._tiles[n]={el:o,coords:t,current:!0},e.appendChild(o),this.fire("tileloadstart",{tile:o,coords:t})},_tileReady:function(t,e,i){e&&this.fire("tileerror",{error:e,tile:i,coords:t});var n=this._tileCoordsToKey(t);i=this._tiles[n],i&&(i.loaded=+new Date,this._map._fadeAnimated?(Mt(i.el,0),y(this._fadeFrame),this._fadeFrame=M(this._updateOpacity,this)):(i.active=!0,this._pruneTiles()),e||(W(i.el,"leaflet-tile-loaded"),this.fire("tileload",{tile:i.el,coords:t})),this._noTilesToLoad()&&(this._loading=!1,this.fire("load"),S.ielt9||!this._map._fadeAnimated?M(this._pruneTiles,this):setTimeout(p(this._pruneTiles,this),250)))},_getTilePos:function(t){return t.scaleBy(this.getTileSize()).subtract(this._level.origin)},_wrapCoords:function(t){var e=new N(this._wrapX?P(t.x,this._wrapX):t.x,this._wrapY?P(t.y,this._wrapY):t.y);return e.z=t.z,e},_pxBoundsToTileRange:function(t){var e=this.getTileSize();return new it(t.min.unscaleBy(e).floor(),t.max.unscaleBy(e).ceil().subtract([1,1]))},_noTilesToLoad:function(){for(var t in this._tiles)if(!this._tiles[t].loaded)return!1;return!0}});function Pr(t){return new ke(t)}var de=ke.extend({options:{minZoom:0,maxZoom:18,subdomains:"abc",errorTileUrl:"",zoomOffset:0,tms:!1,zoomReverse:!1,detectRetina:!1,crossOrigin:!1,referrerPolicy:!1},initialize:function(t,e){this._url=t,e=w(this,e),e.detectRetina&&S.retina&&e.maxZoom>0?(e.tileSize=Math.floor(e.tileSize/2),e.zoomReverse?(e.zoomOffset--,e.minZoom=Math.min(e.maxZoom,e.minZoom+1)):(e.zoomOffset++,e.maxZoom=Math.max(e.minZoom,e.maxZoom-1)),e.minZoom=Math.max(0,e.minZoom)):e.zoomReverse?e.minZoom=Math.min(e.maxZoom,e.minZoom):e.maxZoom=Math.max(e.minZoom,e.maxZoom),typeof e.subdomains=="string"&&(e.subdomains=e.subdomains.split("")),this.on("tileunload",this._onTileRemove)},setUrl:function(t,e){return this._url===t&&e===void 0&&(e=!0),this._url=t,e||this.redraw(),this},createTile:function(t,e){var i=document.createElement("img");return R(i,"load",p(this._tileOnLoad,this,e,i)),R(i,"error",p(this._tileOnError,this,e,i)),(this.options.crossOrigin||this.options.crossOrigin==="")&&(i.crossOrigin=this.options.crossOrigin===!0?"":this.options.crossOrigin),typeof this.options.referrerPolicy=="string"&&(i.referrerPolicy=this.options.referrerPolicy),i.alt="",i.src=this.getTileUrl(t),i},getTileUrl:function(t){var e={r:S.retina?"@2x":"",s:this._getSubdomain(t),x:t.x,y:t.y,z:this._getZoomForUrl()};if(this._map&&!this._map.options.crs.infinite){var i=this._globalTileRange.max.y-t.y;this.options.tms&&(e.y=i),e["-y"]=i}return D(this._url,a(e,this.options))},_tileOnLoad:function(t,e){S.ielt9?setTimeout(p(t,this,null,e),0):t(null,e)},_tileOnError:function(t,e,i){var n=this.options.errorTileUrl;n&&e.getAttribute("src")!==n&&(e.src=n),t(i,e)},_onTileRemove:function(t){t.tile.onload=null},_getZoomForUrl:function(){var t=this._tileZoom,e=this.options.maxZoom,i=this.options.zoomReverse,n=this.options.zoomOffset;return i&&(t=e-t),t+n},_getSubdomain:function(t){var e=Math.abs(t.x+t.y)%this.options.subdomains.length;return this.options.subdomains[e]},_abortLoading:function(){var t,e;for(t in this._tiles)if(this._tiles[t].coords.z!==this._tileZoom&&(e=this._tiles[t].el,e.onload=_,e.onerror=_,!e.complete)){e.src=F;var i=this._tiles[t].coords;st(e),delete this._tiles[t],this.fire("tileabort",{tile:e,coords:i})}},_removeTile:function(t){var e=this._tiles[t];if(e)return e.el.setAttribute("src",F),ke.prototype._removeTile.call(this,t)},_tileReady:function(t,e,i){if(!(!this._map||i&&i.getAttribute("src")===F))return ke.prototype._tileReady.call(this,t,e,i)}});function En(t,e){return new de(t,e)}var Bn=de.extend({defaultWmsParams:{service:"WMS",request:"GetMap",layers:"",styles:"",format:"image/jpeg",transparent:!1,version:"1.1.1"},options:{crs:null,uppercase:!1},initialize:function(t,e){this._url=t;var i=a({},this.defaultWmsParams);for(var n in e)n in this.options||(i[n]=e[n]);e=w(this,e);var o=e.detectRetina&&S.retina?2:1,r=this.getTileSize();i.width=r.x*o,i.height=r.y*o,this.wmsParams=i},onAdd:function(t){this._crs=this.options.crs||t.options.crs,this._wmsVersion=parseFloat(this.wmsParams.version);var e=this._wmsVersion>=1.3?"crs":"srs";this.wmsParams[e]=this._crs.code,de.prototype.onAdd.call(this,t)},getTileUrl:function(t){var e=this._tileCoordsToNwSe(t),i=this._crs,n=dt(i.project(e[0]),i.project(e[1])),o=n.min,r=n.max,c=(this._wmsVersion>=1.3&&this._crs===Ln?[o.y,o.x,r.y,r.x]:[o.x,o.y,r.x,r.y]).join(","),u=de.prototype.getTileUrl.call(this,t);return u+z(this.wmsParams,u,this.options.uppercase)+(this.options.uppercase?"&BBOX=":"&bbox=")+c},setParams:function(t,e){return a(this.wmsParams,t),e||this.redraw(),this}});function Lr(t,e){return new Bn(t,e)}de.WMS=Bn,En.wms=Lr;var Wt=Ot.extend({options:{padding:.1},initialize:function(t){w(this,t),f(this),this._layers=this._layers||{}},onAdd:function(){this._container||(this._initContainer(),W(this._container,"leaflet-zoom-animated")),this.getPane().appendChild(this._container),this._update(),this.on("update",this._updatePaths,this)},onRemove:function(){this.off("update",this._updatePaths,this),this._destroyContainer()},getEvents:function(){var t={viewreset:this._reset,zoom:this._onZoom,moveend:this._update,zoomend:this._onZoomEnd};return this._zoomAnimated&&(t.zoomanim=this._onAnimZoom),t},_onAnimZoom:function(t){this._updateTransform(t.center,t.zoom)},_onZoom:function(){this._updateTransform(this._map.getCenter(),this._map.getZoom())},_updateTransform:function(t,e){var i=this._map.getZoomScale(e,this._zoom),n=this._map.getSize().multiplyBy(.5+this.options.padding),o=this._map.project(this._center,e),r=n.multiplyBy(-i).add(o).subtract(this._map._getNewPixelOrigin(t,e));S.any3d?Kt(this._container,r,i):pt(this._container,r)},_reset:function(){this._update(),this._updateTransform(this._center,this._zoom);for(var t in this._layers)this._layers[t]._reset()},_onZoomEnd:function(){for(var t in this._layers)this._layers[t]._project()},_updatePaths:function(){for(var t in this._layers)this._layers[t]._update()},_update:function(){var t=this.options.padding,e=this._map.getSize(),i=this._map.containerPointToLayerPoint(e.multiplyBy(-t)).round();this._bounds=new it(i,i.add(e.multiplyBy(1+t*2)).round()),this._center=this._map.getCenter(),this._zoom=this._map.getZoom()}}),On=Wt.extend({options:{tolerance:0},getEvents:function(){var t=Wt.prototype.getEvents.call(this);return t.viewprereset=this._onViewPreReset,t},_onViewPreReset:function(){this._postponeUpdatePaths=!0},onAdd:function(){Wt.prototype.onAdd.call(this),this._draw()},_initContainer:function(){var t=this._container=document.createElement("canvas");R(t,"mousemove",this._onMouseMove,this),R(t,"click dblclick mousedown mouseup contextmenu",this._onClick,this),R(t,"mouseout",this._handleMouseOut,this),t._leaflet_disable_events=!0,this._ctx=t.getContext("2d")},_destroyContainer:function(){y(this._redrawRequest),delete this._ctx,st(this._container),et(this._container),delete this._container},_updatePaths:function(){if(!this._postponeUpdatePaths){var t;this._redrawBounds=null;for(var e in this._layers)t=this._layers[e],t._update();this._redraw()}},_update:function(){if(!(this._map._animatingZoom&&this._bounds)){Wt.prototype._update.call(this);var t=this._bounds,e=this._container,i=t.getSize(),n=S.retina?2:1;pt(e,t.min),e.width=n*i.x,e.height=n*i.y,e.style.width=i.x+"px",e.style.height=i.y+"px",S.retina&&this._ctx.scale(2,2),this._ctx.translate(-t.min.x,-t.min.y),this.fire("update")}},_reset:function(){Wt.prototype._reset.call(this),this._postponeUpdatePaths&&(this._postponeUpdatePaths=!1,this._updatePaths())},_initPath:function(t){this._updateDashArray(t),this._layers[f(t)]=t;var e=t._order={layer:t,prev:this._drawLast,next:null};this._drawLast&&(this._drawLast.next=e),this._drawLast=e,this._drawFirst=this._drawFirst||this._drawLast},_addPath:function(t){this._requestRedraw(t)},_removePath:function(t){var e=t._order,i=e.next,n=e.prev;i?i.prev=n:this._drawLast=n,n?n.next=i:this._drawFirst=i,delete t._order,delete this._layers[f(t)],this._requestRedraw(t)},_updatePath:function(t){this._extendRedrawBounds(t),t._project(),t._update(),this._requestRedraw(t)},_updateStyle:function(t){this._updateDashArray(t),this._requestRedraw(t)},_updateDashArray:function(t){if(typeof t.options.dashArray=="string"){var e=t.options.dashArray.split(/[, ]+/),i=[],n,o;for(o=0;o<e.length;o++){if(n=Number(e[o]),isNaN(n))return;i.push(n)}t.options._dashArray=i}else t.options._dashArray=t.options.dashArray},_requestRedraw:function(t){this._map&&(this._extendRedrawBounds(t),this._redrawRequest=this._redrawRequest||M(this._redraw,this))},_extendRedrawBounds:function(t){if(t._pxBounds){var e=(t.options.weight||0)+1;this._redrawBounds=this._redrawBounds||new it,this._redrawBounds.extend(t._pxBounds.min.subtract([e,e])),this._redrawBounds.extend(t._pxBounds.max.add([e,e]))}},_redraw:function(){this._redrawRequest=null,this._redrawBounds&&(this._redrawBounds.min._floor(),this._redrawBounds.max._ceil()),this._clear(),this._draw(),this._redrawBounds=null},_clear:function(){var t=this._redrawBounds;if(t){var e=t.getSize();this._ctx.clearRect(t.min.x,t.min.y,e.x,e.y)}else this._ctx.save(),this._ctx.setTransform(1,0,0,1,0,0),this._ctx.clearRect(0,0,this._container.width,this._container.height),this._ctx.restore()},_draw:function(){var t,e=this._redrawBounds;if(this._ctx.save(),e){var i=e.getSize();this._ctx.beginPath(),this._ctx.rect(e.min.x,e.min.y,i.x,i.y),this._ctx.clip()}this._drawing=!0;for(var n=this._drawFirst;n;n=n.next)t=n.layer,(!e||t._pxBounds&&t._pxBounds.intersects(e))&&t._updatePath();this._drawing=!1,this._ctx.restore()},_updatePoly:function(t,e){if(this._drawing){var i,n,o,r,c=t._parts,u=c.length,m=this._ctx;if(u){for(m.beginPath(),i=0;i<u;i++){for(n=0,o=c[i].length;n<o;n++)r=c[i][n],m[n?"lineTo":"moveTo"](r.x,r.y);e&&m.closePath()}this._fillStroke(m,t)}}},_updateCircle:function(t){if(!(!this._drawing||t._empty())){var e=t._point,i=this._ctx,n=Math.max(Math.round(t._radius),1),o=(Math.max(Math.round(t._radiusY),1)||n)/n;o!==1&&(i.save(),i.scale(1,o)),i.beginPath(),i.arc(e.x,e.y/o,n,0,Math.PI*2,!1),o!==1&&i.restore(),this._fillStroke(i,t)}},_fillStroke:function(t,e){var i=e.options;i.fill&&(t.globalAlpha=i.fillOpacity,t.fillStyle=i.fillColor||i.color,t.fill(i.fillRule||"evenodd")),i.stroke&&i.weight!==0&&(t.setLineDash&&t.setLineDash(e.options&&e.options._dashArray||[]),t.globalAlpha=i.opacity,t.lineWidth=i.weight,t.strokeStyle=i.color,t.lineCap=i.lineCap,t.lineJoin=i.lineJoin,t.stroke())},_onClick:function(t){for(var e=this._map.mouseEventToLayerPoint(t),i,n,o=this._drawFirst;o;o=o.next)i=o.layer,i.options.interactive&&i._containsPoint(e)&&(!(t.type==="click"||t.type==="preclick")||!this._map._draggableMoved(i))&&(n=i);this._fireEvent(n?[n]:!1,t)},_onMouseMove:function(t){if(!(!this._map||this._map.dragging.moving()||this._map._animatingZoom)){var e=this._map.mouseEventToLayerPoint(t);this._handleMouseHover(t,e)}},_handleMouseOut:function(t){var e=this._hoveredLayer;e&&(ht(this._container,"leaflet-interactive"),this._fireEvent([e],t,"mouseout"),this._hoveredLayer=null,this._mouseHoverThrottled=!1)},_handleMouseHover:function(t,e){if(!this._mouseHoverThrottled){for(var i,n,o=this._drawFirst;o;o=o.next)i=o.layer,i.options.interactive&&i._containsPoint(e)&&(n=i);n!==this._hoveredLayer&&(this._handleMouseOut(t),n&&(W(this._container,"leaflet-interactive"),this._fireEvent([n],t,"mouseover"),this._hoveredLayer=n)),this._fireEvent(this._hoveredLayer?[this._hoveredLayer]:!1,t),this._mouseHoverThrottled=!0,setTimeout(p(function(){this._mouseHoverThrottled=!1},this),32)}},_fireEvent:function(t,e,i){this._map._fireDOMEvent(e,i||e.type,t)},_bringToFront:function(t){var e=t._order;if(e){var i=e.next,n=e.prev;if(i)i.prev=n;else return;n?n.next=i:i&&(this._drawFirst=i),e.prev=this._drawLast,this._drawLast.next=e,e.next=null,this._drawLast=e,this._requestRedraw(t)}},_bringToBack:function(t){var e=t._order;if(e){var i=e.next,n=e.prev;if(n)n.next=i;else return;i?i.prev=n:n&&(this._drawLast=n),e.prev=null,e.next=this._drawFirst,this._drawFirst.prev=e,this._drawFirst=e,this._requestRedraw(t)}}});function In(t){return S.canvas?new On(t):null}var Pe=(function(){try{return document.namespaces.add("lvml","urn:schemas-microsoft-com:vml"),function(t){return document.createElement("<lvml:"+t+' class="lvml">')}}catch{}return function(t){return document.createElement("<"+t+' xmlns="urn:schemas-microsoft.com:vml" class="lvml">')}})(),Cr={_initContainer:function(){this._container=Y("div","leaflet-vml-container")},_update:function(){this._map._animatingZoom||(Wt.prototype._update.call(this),this.fire("update"))},_initPath:function(t){var e=t._container=Pe("shape");W(e,"leaflet-vml-shape "+(this.options.className||"")),e.coordsize="1 1",t._path=Pe("path"),e.appendChild(t._path),this._updateStyle(t),this._layers[f(t)]=t},_addPath:function(t){var e=t._container;this._container.appendChild(e),t.options.interactive&&t.addInteractiveTarget(e)},_removePath:function(t){var e=t._container;st(e),t.removeInteractiveTarget(e),delete this._layers[f(t)]},_updateStyle:function(t){var e=t._stroke,i=t._fill,n=t.options,o=t._container;o.stroked=!!n.stroke,o.filled=!!n.fill,n.stroke?(e||(e=t._stroke=Pe("stroke")),o.appendChild(e),e.weight=n.weight+"px",e.color=n.color,e.opacity=n.opacity,n.dashArray?e.dashStyle=A(n.dashArray)?n.dashArray.join(" "):n.dashArray.replace(/( *, *)/g," "):e.dashStyle="",e.endcap=n.lineCap.replace("butt","flat"),e.joinstyle=n.lineJoin):e&&(o.removeChild(e),t._stroke=null),n.fill?(i||(i=t._fill=Pe("fill")),o.appendChild(i),i.color=n.fillColor||n.color,i.opacity=n.fillOpacity):i&&(o.removeChild(i),t._fill=null)},_updateCircle:function(t){var e=t._point.round(),i=Math.round(t._radius),n=Math.round(t._radiusY||i);this._setPath(t,t._empty()?"M0 0":"AL "+e.x+","+e.y+" "+i+","+n+" 0,"+65535*360)},_setPath:function(t,e){t._path.v=e},_bringToFront:function(t){re(t._container)},_bringToBack:function(t){se(t._container)}},$e=S.vml?Pe:Ct,Le=Wt.extend({_initContainer:function(){this._container=$e("svg"),this._container.setAttribute("pointer-events","none"),this._rootGroup=$e("g"),this._container.appendChild(this._rootGroup)},_destroyContainer:function(){st(this._container),et(this._container),delete this._container,delete this._rootGroup,delete this._svgSize},_update:function(){if(!(this._map._animatingZoom&&this._bounds)){Wt.prototype._update.call(this);var t=this._bounds,e=t.getSize(),i=this._container;(!this._svgSize||!this._svgSize.equals(e))&&(this._svgSize=e,i.setAttribute("width",e.x),i.setAttribute("height",e.y)),pt(i,t.min),i.setAttribute("viewBox",[t.min.x,t.min.y,e.x,e.y].join(" ")),this.fire("update")}},_initPath:function(t){var e=t._path=$e("path");t.options.className&&W(e,t.options.className),t.options.interactive&&W(e,"leaflet-interactive"),this._updateStyle(t),this._layers[f(t)]=t},_addPath:function(t){this._rootGroup||this._initContainer(),this._rootGroup.appendChild(t._path),t.addInteractiveTarget(t._path)},_removePath:function(t){st(t._path),t.removeInteractiveTarget(t._path),delete this._layers[f(t)]},_updatePath:function(t){t._project(),t._update()},_updateStyle:function(t){var e=t._path,i=t.options;e&&(i.stroke?(e.setAttribute("stroke",i.color),e.setAttribute("stroke-opacity",i.opacity),e.setAttribute("stroke-width",i.weight),e.setAttribute("stroke-linecap",i.lineCap),e.setAttribute("stroke-linejoin",i.lineJoin),i.dashArray?e.setAttribute("stroke-dasharray",i.dashArray):e.removeAttribute("stroke-dasharray"),i.dashOffset?e.setAttribute("stroke-dashoffset",i.dashOffset):e.removeAttribute("stroke-dashoffset")):e.setAttribute("stroke","none"),i.fill?(e.setAttribute("fill",i.fillColor||i.color),e.setAttribute("fill-opacity",i.fillOpacity),e.setAttribute("fill-rule",i.fillRule||"evenodd")):e.setAttribute("fill","none"))},_updatePoly:function(t,e){this._setPath(t,G(t._parts,e))},_updateCircle:function(t){var e=t._point,i=Math.max(Math.round(t._radius),1),n=Math.max(Math.round(t._radiusY),1)||i,o="a"+i+","+n+" 0 1,0 ",r=t._empty()?"M0 0":"M"+(e.x-i)+","+e.y+o+i*2+",0 "+o+-i*2+",0 ";this._setPath(t,r)},_setPath:function(t,e){t._path.setAttribute("d",e)},_bringToFront:function(t){re(t._path)},_bringToBack:function(t){se(t._path)}});S.vml&&Le.include(Cr);function Nn(t){return S.svg||S.vml?new Le(t):null}V.include({getRenderer:function(t){var e=t.options.renderer||this._getPaneRenderer(t.options.pane)||this.options.renderer||this._renderer;return e||(e=this._renderer=this._createRenderer()),this.hasLayer(e)||this.addLayer(e),e},_getPaneRenderer:function(t){if(t==="overlayPane"||t===void 0)return!1;var e=this._paneRenderers[t];return e===void 0&&(e=this._createRenderer({pane:t}),this._paneRenderers[t]=e),e},_createRenderer:function(t){return this.options.preferCanvas&&In(t)||Nn(t)}});var Zn=he.extend({initialize:function(t,e){he.prototype.initialize.call(this,this._boundsToLatLngs(t),e)},setBounds:function(t){return this.setLatLngs(this._boundsToLatLngs(t))},_boundsToLatLngs:function(t){return t=rt(t),[t.getSouthWest(),t.getNorthWest(),t.getNorthEast(),t.getSouthEast()]}});function Tr(t,e){return new Zn(t,e)}Le.create=$e,Le.pointsToPath=G,Ft.geometryToLayer=Re,Ft.coordsToLatLng=Ci,Ft.coordsToLatLngs=He,Ft.latLngToCoords=Ti,Ft.latLngsToCoords=De,Ft.getFeature=ce,Ft.asFeature=Fe,V.mergeOptions({boxZoom:!0});var Rn=Zt.extend({initialize:function(t){this._map=t,this._container=t._container,this._pane=t._panes.overlayPane,this._resetStateTimeout=0,t.on("unload",this._destroy,this)},addHooks:function(){R(this._container,"mousedown",this._onMouseDown,this)},removeHooks:function(){et(this._container,"mousedown",this._onMouseDown,this)},moved:function(){return this._moved},_destroy:function(){st(this._pane),delete this._pane},_resetState:function(){this._resetStateTimeout=0,this._moved=!1},_clearDeferredResetState:function(){this._resetStateTimeout!==0&&(clearTimeout(this._resetStateTimeout),this._resetStateTimeout=0)},_onMouseDown:function(t){if(!t.shiftKey||t.which!==1&&t.button!==1)return!1;this._clearDeferredResetState(),this._resetState(),_e(),hi(),this._startPoint=this._map.mouseEventToContainerPoint(t),R(document,{contextmenu:Jt,mousemove:this._onMouseMove,mouseup:this._onMouseUp,keydown:this._onKeyDown},this)},_onMouseMove:function(t){this._moved||(this._moved=!0,this._box=Y("div","leaflet-zoom-box",this._container),W(this._container,"leaflet-crosshair"),this._map.fire("boxzoomstart")),this._point=this._map.mouseEventToContainerPoint(t);var e=new it(this._point,this._startPoint),i=e.getSize();pt(this._box,e.min),this._box.style.width=i.x+"px",this._box.style.height=i.y+"px"},_finish:function(){this._moved&&(st(this._box),ht(this._container,"leaflet-crosshair")),ge(),ci(),et(document,{contextmenu:Jt,mousemove:this._onMouseMove,mouseup:this._onMouseUp,keydown:this._onKeyDown},this)},_onMouseUp:function(t){if(!(t.which!==1&&t.button!==1)&&(this._finish(),!!this._moved)){this._clearDeferredResetState(),this._resetStateTimeout=setTimeout(p(this._resetState,this),0);var e=new gt(this._map.containerPointToLatLng(this._startPoint),this._map.containerPointToLatLng(this._point));this._map.fitBounds(e).fire("boxzoomend",{boxZoomBounds:e})}},_onKeyDown:function(t){t.keyCode===27&&(this._finish(),this._clearDeferredResetState(),this._resetState())}});V.addInitHook("addHandler","boxZoom",Rn),V.mergeOptions({doubleClickZoom:!0});var Hn=Zt.extend({addHooks:function(){this._map.on("dblclick",this._onDoubleClick,this)},removeHooks:function(){this._map.off("dblclick",this._onDoubleClick,this)},_onDoubleClick:function(t){var e=this._map,i=e.getZoom(),n=e.options.zoomDelta,o=t.originalEvent.shiftKey?i-n:i+n;e.options.doubleClickZoom==="center"?e.setZoom(o):e.setZoomAround(t.containerPoint,o)}});V.addInitHook("addHandler","doubleClickZoom",Hn),V.mergeOptions({dragging:!0,inertia:!0,inertiaDeceleration:3400,inertiaMaxSpeed:1/0,easeLinearity:.2,worldCopyJump:!1,maxBoundsViscosity:0});var Dn=Zt.extend({addHooks:function(){if(!this._draggable){var t=this._map;this._draggable=new Gt(t._mapPane,t._container),this._draggable.on({dragstart:this._onDragStart,drag:this._onDrag,dragend:this._onDragEnd},this),this._draggable.on("predrag",this._onPreDragLimit,this),t.options.worldCopyJump&&(this._draggable.on("predrag",this._onPreDragWrap,this),t.on("zoomend",this._onZoomEnd,this),t.whenReady(this._onZoomEnd,this))}W(this._map._container,"leaflet-grab leaflet-touch-drag"),this._draggable.enable(),this._positions=[],this._times=[]},removeHooks:function(){ht(this._map._container,"leaflet-grab"),ht(this._map._container,"leaflet-touch-drag"),this._draggable.disable()},moved:function(){return this._draggable&&this._draggable._moved},moving:function(){return this._draggable&&this._draggable._moving},_onDragStart:function(){var t=this._map;if(t._stop(),this._map.options.maxBounds&&this._map.options.maxBoundsViscosity){var e=rt(this._map.options.maxBounds);this._offsetLimit=dt(this._map.latLngToContainerPoint(e.getNorthWest()).multiplyBy(-1),this._map.latLngToContainerPoint(e.getSouthEast()).multiplyBy(-1).add(this._map.getSize())),this._viscosity=Math.min(1,Math.max(0,this._map.options.maxBoundsViscosity))}else this._offsetLimit=null;t.fire("movestart").fire("dragstart"),t.options.inertia&&(this._positions=[],this._times=[])},_onDrag:function(t){if(this._map.options.inertia){var e=this._lastTime=+new Date,i=this._lastPos=this._draggable._absPos||this._draggable._newPos;this._positions.push(i),this._times.push(e),this._prunePositions(e)}this._map.fire("move",t).fire("drag",t)},_prunePositions:function(t){for(;this._positions.length>1&&t-this._times[0]>50;)this._positions.shift(),this._times.shift()},_onZoomEnd:function(){var t=this._map.getSize().divideBy(2),e=this._map.latLngToLayerPoint([0,0]);this._initialWorldOffset=e.subtract(t).x,this._worldWidth=this._map.getPixelWorldBounds().getSize().x},_viscousLimit:function(t,e){return t-(t-e)*this._viscosity},_onPreDragLimit:function(){if(!(!this._viscosity||!this._offsetLimit)){var t=this._draggable._newPos.subtract(this._draggable._startPos),e=this._offsetLimit;t.x<e.min.x&&(t.x=this._viscousLimit(t.x,e.min.x)),t.y<e.min.y&&(t.y=this._viscousLimit(t.y,e.min.y)),t.x>e.max.x&&(t.x=this._viscousLimit(t.x,e.max.x)),t.y>e.max.y&&(t.y=this._viscousLimit(t.y,e.max.y)),this._draggable._newPos=this._draggable._startPos.add(t)}},_onPreDragWrap:function(){var t=this._worldWidth,e=Math.round(t/2),i=this._initialWorldOffset,n=this._draggable._newPos.x,o=(n-e+i)%t+e-i,r=(n+e+i)%t-e-i,c=Math.abs(o+i)<Math.abs(r+i)?o:r;this._draggable._absPos=this._draggable._newPos.clone(),this._draggable._newPos.x=c},_onDragEnd:function(t){var e=this._map,i=e.options,n=!i.inertia||t.noInertia||this._times.length<2;if(e.fire("dragend",t),n)e.fire("moveend");else{this._prunePositions(+new Date);var o=this._lastPos.subtract(this._positions[0]),r=(this._lastTime-this._times[0])/1e3,c=i.easeLinearity,u=o.multiplyBy(c/r),m=u.distanceTo([0,0]),v=Math.min(i.inertiaMaxSpeed,m),k=u.multiplyBy(v/m),B=v/(i.inertiaDeceleration*c),$=k.multiplyBy(-B/2).round();!$.x&&!$.y?e.fire("moveend"):($=e._limitOffset($,e.options.maxBounds),M(function(){e.panBy($,{duration:B,easeLinearity:c,noMoveStart:!0,animate:!0})}))}}});V.addInitHook("addHandler","dragging",Dn),V.mergeOptions({keyboard:!0,keyboardPanDelta:80});var Fn=Zt.extend({keyCodes:{left:[37],right:[39],down:[40],up:[38],zoomIn:[187,107,61,171],zoomOut:[189,109,54,173]},initialize:function(t){this._map=t,this._setPanDelta(t.options.keyboardPanDelta),this._setZoomDelta(t.options.zoomDelta)},addHooks:function(){var t=this._map._container;t.tabIndex<=0&&(t.tabIndex="0"),R(t,{focus:this._onFocus,blur:this._onBlur,mousedown:this._onMouseDown},this),this._map.on({focus:this._addHooks,blur:this._removeHooks},this)},removeHooks:function(){this._removeHooks(),et(this._map._container,{focus:this._onFocus,blur:this._onBlur,mousedown:this._onMouseDown},this),this._map.off({focus:this._addHooks,blur:this._removeHooks},this)},_onMouseDown:function(){if(!this._focused){var t=document.body,e=document.documentElement,i=t.scrollTop||e.scrollTop,n=t.scrollLeft||e.scrollLeft;this._map._container.focus(),window.scrollTo(n,i)}},_onFocus:function(){this._focused=!0,this._map.fire("focus")},_onBlur:function(){this._focused=!1,this._map.fire("blur")},_setPanDelta:function(t){var e=this._panKeys={},i=this.keyCodes,n,o;for(n=0,o=i.left.length;n<o;n++)e[i.left[n]]=[-1*t,0];for(n=0,o=i.right.length;n<o;n++)e[i.right[n]]=[t,0];for(n=0,o=i.down.length;n<o;n++)e[i.down[n]]=[0,t];for(n=0,o=i.up.length;n<o;n++)e[i.up[n]]=[0,-1*t]},_setZoomDelta:function(t){var e=this._zoomKeys={},i=this.keyCodes,n,o;for(n=0,o=i.zoomIn.length;n<o;n++)e[i.zoomIn[n]]=t;for(n=0,o=i.zoomOut.length;n<o;n++)e[i.zoomOut[n]]=-t},_addHooks:function(){R(document,"keydown",this._onKeyDown,this)},_removeHooks:function(){et(document,"keydown",this._onKeyDown,this)},_onKeyDown:function(t){if(!(t.altKey||t.ctrlKey||t.metaKey)){var e=t.keyCode,i=this._map,n;if(e in this._panKeys){if(!i._panAnim||!i._panAnim._inProgress)if(n=this._panKeys[e],t.shiftKey&&(n=I(n).multiplyBy(3)),i.options.maxBounds&&(n=i._limitOffset(I(n),i.options.maxBounds)),i.options.worldCopyJump){var o=i.wrapLatLng(i.unproject(i.project(i.getCenter()).add(n)));i.panTo(o)}else i.panBy(n)}else if(e in this._zoomKeys)i.setZoom(i.getZoom()+(t.shiftKey?3:1)*this._zoomKeys[e]);else if(e===27&&i._popup&&i._popup.options.closeOnEscapeKey)i.closePopup();else return;Jt(t)}}});V.addInitHook("addHandler","keyboard",Fn),V.mergeOptions({scrollWheelZoom:!0,wheelDebounceTime:40,wheelPxPerZoomLevel:60});var Wn=Zt.extend({addHooks:function(){R(this._map._container,"wheel",this._onWheelScroll,this),this._delta=0},removeHooks:function(){et(this._map._container,"wheel",this._onWheelScroll,this)},_onWheelScroll:function(t){var e=un(t),i=this._map.options.wheelDebounceTime;this._delta+=e,this._lastMousePos=this._map.mouseEventToContainerPoint(t),this._startTime||(this._startTime=+new Date);var n=Math.max(i-(+new Date-this._startTime),0);clearTimeout(this._timer),this._timer=setTimeout(p(this._performZoom,this),n),Jt(t)},_performZoom:function(){var t=this._map,e=t.getZoom(),i=this._map.options.zoomSnap||0;t._stop();var n=this._delta/(this._map.options.wheelPxPerZoomLevel*4),o=4*Math.log(2/(1+Math.exp(-Math.abs(n))))/Math.LN2,r=i?Math.ceil(o/i)*i:o,c=t._limitZoom(e+(this._delta>0?r:-r))-e;this._delta=0,this._startTime=null,c&&(t.options.scrollWheelZoom==="center"?t.setZoom(e+c):t.setZoomAround(this._lastMousePos,e+c))}});V.addInitHook("addHandler","scrollWheelZoom",Wn);var Mr=600;V.mergeOptions({tapHold:S.touchNative&&S.safari&&S.mobile,tapTolerance:15});var qn=Zt.extend({addHooks:function(){R(this._map._container,"touchstart",this._onDown,this)},removeHooks:function(){et(this._map._container,"touchstart",this._onDown,this)},_onDown:function(t){if(clearTimeout(this._holdTimeout),t.touches.length===1){var e=t.touches[0];this._startPos=this._newPos=new N(e.clientX,e.clientY),this._holdTimeout=setTimeout(p(function(){this._cancel(),this._isTapValid()&&(R(document,"touchend",vt),R(document,"touchend touchcancel",this._cancelClickPrevent),this._simulateEvent("contextmenu",e))},this),Mr),R(document,"touchend touchcancel contextmenu",this._cancel,this),R(document,"touchmove",this._onMove,this)}},_cancelClickPrevent:function t(){et(document,"touchend",vt),et(document,"touchend touchcancel",t)},_cancel:function(){clearTimeout(this._holdTimeout),et(document,"touchend touchcancel contextmenu",this._cancel,this),et(document,"touchmove",this._onMove,this)},_onMove:function(t){var e=t.touches[0];this._newPos=new N(e.clientX,e.clientY)},_isTapValid:function(){return this._newPos.distanceTo(this._startPos)<=this._map.options.tapTolerance},_simulateEvent:function(t,e){var i=new MouseEvent(t,{bubbles:!0,cancelable:!0,view:window,screenX:e.screenX,screenY:e.screenY,clientX:e.clientX,clientY:e.clientY});i._simulated=!0,e.target.dispatchEvent(i)}});V.addInitHook("addHandler","tapHold",qn),V.mergeOptions({touchZoom:S.touch,bounceAtZoomLimits:!0});var Un=Zt.extend({addHooks:function(){W(this._map._container,"leaflet-touch-zoom"),R(this._map._container,"touchstart",this._onTouchStart,this)},removeHooks:function(){ht(this._map._container,"leaflet-touch-zoom"),et(this._map._container,"touchstart",this._onTouchStart,this)},_onTouchStart:function(t){var e=this._map;if(!(!t.touches||t.touches.length!==2||e._animatingZoom||this._zooming)){var i=e.mouseEventToContainerPoint(t.touches[0]),n=e.mouseEventToContainerPoint(t.touches[1]);this._centerPoint=e.getSize()._divideBy(2),this._startLatLng=e.containerPointToLatLng(this._centerPoint),e.options.touchZoom!=="center"&&(this._pinchStartLatLng=e.containerPointToLatLng(i.add(n)._divideBy(2))),this._startDist=i.distanceTo(n),this._startZoom=e.getZoom(),this._moved=!1,this._zooming=!0,e._stop(),R(document,"touchmove",this._onTouchMove,this),R(document,"touchend touchcancel",this._onTouchEnd,this),vt(t)}},_onTouchMove:function(t){if(!(!t.touches||t.touches.length!==2||!this._zooming)){var e=this._map,i=e.mouseEventToContainerPoint(t.touches[0]),n=e.mouseEventToContainerPoint(t.touches[1]),o=i.distanceTo(n)/this._startDist;if(this._zoom=e.getScaleZoom(o,this._startZoom),!e.options.bounceAtZoomLimits&&(this._zoom<e.getMinZoom()&&o<1||this._zoom>e.getMaxZoom()&&o>1)&&(this._zoom=e._limitZoom(this._zoom)),e.options.touchZoom==="center"){if(this._center=this._startLatLng,o===1)return}else{var r=i._add(n)._divideBy(2)._subtract(this._centerPoint);if(o===1&&r.x===0&&r.y===0)return;this._center=e.unproject(e.project(this._pinchStartLatLng,this._zoom).subtract(r),this._zoom)}this._moved||(e._moveStart(!0,!1),this._moved=!0),y(this._animRequest);var c=p(e._move,e,this._center,this._zoom,{pinch:!0,round:!1},void 0);this._animRequest=M(c,this,!0),vt(t)}},_onTouchEnd:function(){if(!this._moved||!this._zooming){this._zooming=!1;return}this._zooming=!1,y(this._animRequest),et(document,"touchmove",this._onTouchMove,this),et(document,"touchend touchcancel",this._onTouchEnd,this),this._map.options.zoomAnimation?this._map._animateZoom(this._center,this._map._limitZoom(this._zoom),!0,this._map.options.zoomSnap):this._map._resetView(this._center,this._map._limitZoom(this._zoom))}});V.addInitHook("addHandler","touchZoom",Un),V.BoxZoom=Rn,V.DoubleClickZoom=Hn,V.Drag=Dn,V.Keyboard=Fn,V.ScrollWheelZoom=Wn,V.TapHold=qn,V.TouchZoom=Un,l.Bounds=it,l.Browser=S,l.CRS=kt,l.Canvas=On,l.Circle=Li,l.CircleMarker=Ze,l.Class=Q,l.Control=Bt,l.DivIcon=An,l.DivOverlay=Rt,l.DomEvent=Go,l.DomUtil=Uo,l.Draggable=Gt,l.Evented=wt,l.FeatureGroup=Ht,l.GeoJSON=Ft,l.GridLayer=ke,l.Handler=Zt,l.Icon=le,l.ImageOverlay=We,l.LatLng=K,l.LatLngBounds=gt,l.Layer=Ot,l.LayerGroup=ae,l.LineUtil=rr,l.Map=V,l.Marker=Ne,l.Mixin=Qo,l.Path=Vt,l.Point=N,l.PolyUtil=tr,l.Polygon=he,l.Polyline=Dt,l.Popup=qe,l.PosAnimation=pn,l.Projection=sr,l.Rectangle=Zn,l.Renderer=Wt,l.SVG=Le,l.SVGOverlay=zn,l.TileLayer=de,l.Tooltip=Ue,l.Transformation=At,l.Util=J,l.VideoOverlay=Sn,l.bind=p,l.bounds=dt,l.canvas=In,l.circle=fr,l.circleMarker=pr,l.control=be,l.divIcon=kr,l.extend=a,l.featureGroup=cr,l.geoJSON=Mn,l.geoJson=gr,l.gridLayer=Pr,l.icon=dr,l.imageOverlay=vr,l.latLng=U,l.latLngBounds=rt,l.layerGroup=hr,l.map=Vo,l.marker=ur,l.point=I,l.polygon=_r,l.polyline=mr,l.popup=xr,l.rectangle=Tr,l.setOptions=w,l.stamp=f,l.svg=Nn,l.svgOverlay=br,l.tileLayer=En,l.tooltip=wr,l.transformation=tt,l.version=s,l.videoOverlay=yr;var Sr=window.L;l.noConflict=function(){return window.L=Sr,this},window.L=l}))});function $r(l){return l.split(/\s+/).map(s=>s[0]).slice(0,2).join("").toUpperCase()}function Gr(l){if(typeof l!="string"||/[\x00-\x1f\\]/.test(l)||l.includes("/../")||/%2e/i.test(l))return!1;if(l.startsWith("/api/image/serve/")||l.startsWith("/local/"))return!0;try{let s=new URL(l),a=decodeURIComponent(s.pathname);if(a.split("/").some(p=>p==="."||p===".."))return!1;let d=s.host==="www.life360.com"&&a.startsWith("/img/user_images/")||s.host==="life360-images-pub.life360.com"&&/\.(jpeg|jpg|png|webp)$/.test(a);return s.protocol==="https:"&&d&&!s.hash}catch{return!1}}function te(l,s="marker-avatar"){let a=document.createElement("span");if(a.className=s,a.textContent=$r(l.name),a.setAttribute("aria-hidden","true"),Gr(l.picture)){let d=document.createElement("img");d.alt="",d.referrerPolicy="no-referrer",d.src=l.picture,d.addEventListener("error",()=>d.remove(),{once:!0}),a.append(d)}return a}var _t=Kn(zi(),1);var Xn=`/* required styles */\r
\r
.leaflet-pane,\r
.leaflet-tile,\r
.leaflet-marker-icon,\r
.leaflet-marker-shadow,\r
.leaflet-tile-container,\r
.leaflet-pane > svg,\r
.leaflet-pane > canvas,\r
.leaflet-zoom-box,\r
.leaflet-image-layer,\r
.leaflet-layer {\r
	position: absolute;\r
	left: 0;\r
	top: 0;\r
	}\r
.leaflet-container {\r
	overflow: hidden;\r
	}\r
.leaflet-tile,\r
.leaflet-marker-icon,\r
.leaflet-marker-shadow {\r
	-webkit-user-select: none;\r
	   -moz-user-select: none;\r
	        user-select: none;\r
	  -webkit-user-drag: none;\r
	}\r
/* Prevents IE11 from highlighting tiles in blue */\r
.leaflet-tile::selection {\r
	background: transparent;\r
}\r
/* Safari renders non-retina tile on retina better with this, but Chrome is worse */\r
.leaflet-safari .leaflet-tile {\r
	image-rendering: -webkit-optimize-contrast;\r
	}\r
/* hack that prevents hw layers "stretching" when loading new tiles */\r
.leaflet-safari .leaflet-tile-container {\r
	width: 1600px;\r
	height: 1600px;\r
	-webkit-transform-origin: 0 0;\r
	}\r
.leaflet-marker-icon,\r
.leaflet-marker-shadow {\r
	display: block;\r
	}\r
/* .leaflet-container svg: reset svg max-width decleration shipped in Joomla! (joomla.org) 3.x */\r
/* .leaflet-container img: map is broken in FF if you have max-width: 100% on tiles */\r
.leaflet-container .leaflet-overlay-pane svg {\r
	max-width: none !important;\r
	max-height: none !important;\r
	}\r
.leaflet-container .leaflet-marker-pane img,\r
.leaflet-container .leaflet-shadow-pane img,\r
.leaflet-container .leaflet-tile-pane img,\r
.leaflet-container img.leaflet-image-layer,\r
.leaflet-container .leaflet-tile {\r
	max-width: none !important;\r
	max-height: none !important;\r
	width: auto;\r
	padding: 0;\r
	}\r
\r
.leaflet-container img.leaflet-tile {\r
	/* See: https://bugs.chromium.org/p/chromium/issues/detail?id=600120 */\r
	mix-blend-mode: plus-lighter;\r
}\r
\r
.leaflet-container.leaflet-touch-zoom {\r
	-ms-touch-action: pan-x pan-y;\r
	touch-action: pan-x pan-y;\r
	}\r
.leaflet-container.leaflet-touch-drag {\r
	-ms-touch-action: pinch-zoom;\r
	/* Fallback for FF which doesn't support pinch-zoom */\r
	touch-action: none;\r
	touch-action: pinch-zoom;\r
}\r
.leaflet-container.leaflet-touch-drag.leaflet-touch-zoom {\r
	-ms-touch-action: none;\r
	touch-action: none;\r
}\r
.leaflet-container {\r
	-webkit-tap-highlight-color: transparent;\r
}\r
.leaflet-container a {\r
	-webkit-tap-highlight-color: rgba(51, 181, 229, 0.4);\r
}\r
.leaflet-tile {\r
	filter: inherit;\r
	visibility: hidden;\r
	}\r
.leaflet-tile-loaded {\r
	visibility: inherit;\r
	}\r
.leaflet-zoom-box {\r
	width: 0;\r
	height: 0;\r
	-moz-box-sizing: border-box;\r
	     box-sizing: border-box;\r
	z-index: 800;\r
	}\r
/* workaround for https://bugzilla.mozilla.org/show_bug.cgi?id=888319 */\r
.leaflet-overlay-pane svg {\r
	-moz-user-select: none;\r
	}\r
\r
.leaflet-pane         { z-index: 400; }\r
\r
.leaflet-tile-pane    { z-index: 200; }\r
.leaflet-overlay-pane { z-index: 400; }\r
.leaflet-shadow-pane  { z-index: 500; }\r
.leaflet-marker-pane  { z-index: 600; }\r
.leaflet-tooltip-pane   { z-index: 650; }\r
.leaflet-popup-pane   { z-index: 700; }\r
\r
.leaflet-map-pane canvas { z-index: 100; }\r
.leaflet-map-pane svg    { z-index: 200; }\r
\r
.leaflet-vml-shape {\r
	width: 1px;\r
	height: 1px;\r
	}\r
.lvml {\r
	behavior: url(#default#VML);\r
	display: inline-block;\r
	position: absolute;\r
	}\r
\r
\r
/* control positioning */\r
\r
.leaflet-control {\r
	position: relative;\r
	z-index: 800;\r
	pointer-events: visiblePainted; /* IE 9-10 doesn't have auto */\r
	pointer-events: auto;\r
	}\r
.leaflet-top,\r
.leaflet-bottom {\r
	position: absolute;\r
	z-index: 1000;\r
	pointer-events: none;\r
	}\r
.leaflet-top {\r
	top: 0;\r
	}\r
.leaflet-right {\r
	right: 0;\r
	}\r
.leaflet-bottom {\r
	bottom: 0;\r
	}\r
.leaflet-left {\r
	left: 0;\r
	}\r
.leaflet-control {\r
	float: left;\r
	clear: both;\r
	}\r
.leaflet-right .leaflet-control {\r
	float: right;\r
	}\r
.leaflet-top .leaflet-control {\r
	margin-top: 10px;\r
	}\r
.leaflet-bottom .leaflet-control {\r
	margin-bottom: 10px;\r
	}\r
.leaflet-left .leaflet-control {\r
	margin-left: 10px;\r
	}\r
.leaflet-right .leaflet-control {\r
	margin-right: 10px;\r
	}\r
\r
\r
/* zoom and fade animations */\r
\r
.leaflet-fade-anim .leaflet-popup {\r
	opacity: 0;\r
	-webkit-transition: opacity 0.2s linear;\r
	   -moz-transition: opacity 0.2s linear;\r
	        transition: opacity 0.2s linear;\r
	}\r
.leaflet-fade-anim .leaflet-map-pane .leaflet-popup {\r
	opacity: 1;\r
	}\r
.leaflet-zoom-animated {\r
	-webkit-transform-origin: 0 0;\r
	    -ms-transform-origin: 0 0;\r
	        transform-origin: 0 0;\r
	}\r
svg.leaflet-zoom-animated {\r
	will-change: transform;\r
}\r
\r
.leaflet-zoom-anim .leaflet-zoom-animated {\r
	-webkit-transition: -webkit-transform 0.25s cubic-bezier(0,0,0.25,1);\r
	   -moz-transition:    -moz-transform 0.25s cubic-bezier(0,0,0.25,1);\r
	        transition:         transform 0.25s cubic-bezier(0,0,0.25,1);\r
	}\r
.leaflet-zoom-anim .leaflet-tile,\r
.leaflet-pan-anim .leaflet-tile {\r
	-webkit-transition: none;\r
	   -moz-transition: none;\r
	        transition: none;\r
	}\r
\r
.leaflet-zoom-anim .leaflet-zoom-hide {\r
	visibility: hidden;\r
	}\r
\r
\r
/* cursors */\r
\r
.leaflet-interactive {\r
	cursor: pointer;\r
	}\r
.leaflet-grab {\r
	cursor: -webkit-grab;\r
	cursor:    -moz-grab;\r
	cursor:         grab;\r
	}\r
.leaflet-crosshair,\r
.leaflet-crosshair .leaflet-interactive {\r
	cursor: crosshair;\r
	}\r
.leaflet-popup-pane,\r
.leaflet-control {\r
	cursor: auto;\r
	}\r
.leaflet-dragging .leaflet-grab,\r
.leaflet-dragging .leaflet-grab .leaflet-interactive,\r
.leaflet-dragging .leaflet-marker-draggable {\r
	cursor: move;\r
	cursor: -webkit-grabbing;\r
	cursor:    -moz-grabbing;\r
	cursor:         grabbing;\r
	}\r
\r
/* marker & overlays interactivity */\r
.leaflet-marker-icon,\r
.leaflet-marker-shadow,\r
.leaflet-image-layer,\r
.leaflet-pane > svg path,\r
.leaflet-tile-container {\r
	pointer-events: none;\r
	}\r
\r
.leaflet-marker-icon.leaflet-interactive,\r
.leaflet-image-layer.leaflet-interactive,\r
.leaflet-pane > svg path.leaflet-interactive,\r
svg.leaflet-image-layer.leaflet-interactive path {\r
	pointer-events: visiblePainted; /* IE 9-10 doesn't have auto */\r
	pointer-events: auto;\r
	}\r
\r
/* visual tweaks */\r
\r
.leaflet-container {\r
	background: #ddd;\r
	outline-offset: 1px;\r
	}\r
.leaflet-container a {\r
	color: #0078A8;\r
	}\r
.leaflet-zoom-box {\r
	border: 2px dotted #38f;\r
	background: rgba(255,255,255,0.5);\r
	}\r
\r
\r
/* general typography */\r
.leaflet-container {\r
	font-family: "Helvetica Neue", Arial, Helvetica, sans-serif;\r
	font-size: 12px;\r
	font-size: 0.75rem;\r
	line-height: 1.5;\r
	}\r
\r
\r
/* general toolbar styles */\r
\r
.leaflet-bar {\r
	box-shadow: 0 1px 5px rgba(0,0,0,0.65);\r
	border-radius: 4px;\r
	}\r
.leaflet-bar a {\r
	background-color: #fff;\r
	border-bottom: 1px solid #ccc;\r
	width: 26px;\r
	height: 26px;\r
	line-height: 26px;\r
	display: block;\r
	text-align: center;\r
	text-decoration: none;\r
	color: black;\r
	}\r
.leaflet-bar a,\r
.leaflet-control-layers-toggle {\r
	background-position: 50% 50%;\r
	background-repeat: no-repeat;\r
	display: block;\r
	}\r
.leaflet-bar a:hover,\r
.leaflet-bar a:focus {\r
	background-color: #f4f4f4;\r
	}\r
.leaflet-bar a:first-child {\r
	border-top-left-radius: 4px;\r
	border-top-right-radius: 4px;\r
	}\r
.leaflet-bar a:last-child {\r
	border-bottom-left-radius: 4px;\r
	border-bottom-right-radius: 4px;\r
	border-bottom: none;\r
	}\r
.leaflet-bar a.leaflet-disabled {\r
	cursor: default;\r
	background-color: #f4f4f4;\r
	color: #bbb;\r
	}\r
\r
.leaflet-touch .leaflet-bar a {\r
	width: 30px;\r
	height: 30px;\r
	line-height: 30px;\r
	}\r
.leaflet-touch .leaflet-bar a:first-child {\r
	border-top-left-radius: 2px;\r
	border-top-right-radius: 2px;\r
	}\r
.leaflet-touch .leaflet-bar a:last-child {\r
	border-bottom-left-radius: 2px;\r
	border-bottom-right-radius: 2px;\r
	}\r
\r
/* zoom control */\r
\r
.leaflet-control-zoom-in,\r
.leaflet-control-zoom-out {\r
	font: bold 18px 'Lucida Console', Monaco, monospace;\r
	text-indent: 1px;\r
	}\r
\r
.leaflet-touch .leaflet-control-zoom-in, .leaflet-touch .leaflet-control-zoom-out  {\r
	font-size: 22px;\r
	}\r
\r
\r
/* layers control */\r
\r
.leaflet-control-layers {\r
	box-shadow: 0 1px 5px rgba(0,0,0,0.4);\r
	background: #fff;\r
	border-radius: 5px;\r
	}\r
.leaflet-control-layers-toggle {\r
	background-image: url(images/layers.png);\r
	width: 36px;\r
	height: 36px;\r
	}\r
.leaflet-retina .leaflet-control-layers-toggle {\r
	background-image: url(images/layers-2x.png);\r
	background-size: 26px 26px;\r
	}\r
.leaflet-touch .leaflet-control-layers-toggle {\r
	width: 44px;\r
	height: 44px;\r
	}\r
.leaflet-control-layers .leaflet-control-layers-list,\r
.leaflet-control-layers-expanded .leaflet-control-layers-toggle {\r
	display: none;\r
	}\r
.leaflet-control-layers-expanded .leaflet-control-layers-list {\r
	display: block;\r
	position: relative;\r
	}\r
.leaflet-control-layers-expanded {\r
	padding: 6px 10px 6px 6px;\r
	color: #333;\r
	background: #fff;\r
	}\r
.leaflet-control-layers-scrollbar {\r
	overflow-y: scroll;\r
	overflow-x: hidden;\r
	padding-right: 5px;\r
	}\r
.leaflet-control-layers-selector {\r
	margin-top: 2px;\r
	position: relative;\r
	top: 1px;\r
	}\r
.leaflet-control-layers label {\r
	display: block;\r
	font-size: 13px;\r
	font-size: 1.08333em;\r
	}\r
.leaflet-control-layers-separator {\r
	height: 0;\r
	border-top: 1px solid #ddd;\r
	margin: 5px -10px 5px -6px;\r
	}\r
\r
/* Default icon URLs */\r
.leaflet-default-icon-path { /* used only in path-guessing heuristic, see L.Icon.Default */\r
	background-image: url(images/marker-icon.png);\r
	}\r
\r
\r
/* attribution and scale controls */\r
\r
.leaflet-container .leaflet-control-attribution {\r
	background: #fff;\r
	background: rgba(255, 255, 255, 0.8);\r
	margin: 0;\r
	}\r
.leaflet-control-attribution,\r
.leaflet-control-scale-line {\r
	padding: 0 5px;\r
	color: #333;\r
	line-height: 1.4;\r
	}\r
.leaflet-control-attribution a {\r
	text-decoration: none;\r
	}\r
.leaflet-control-attribution a:hover,\r
.leaflet-control-attribution a:focus {\r
	text-decoration: underline;\r
	}\r
.leaflet-attribution-flag {\r
	display: inline !important;\r
	vertical-align: baseline !important;\r
	width: 1em;\r
	height: 0.6669em;\r
	}\r
.leaflet-left .leaflet-control-scale {\r
	margin-left: 5px;\r
	}\r
.leaflet-bottom .leaflet-control-scale {\r
	margin-bottom: 5px;\r
	}\r
.leaflet-control-scale-line {\r
	border: 2px solid #777;\r
	border-top: none;\r
	line-height: 1.1;\r
	padding: 2px 5px 1px;\r
	white-space: nowrap;\r
	-moz-box-sizing: border-box;\r
	     box-sizing: border-box;\r
	background: rgba(255, 255, 255, 0.8);\r
	text-shadow: 1px 1px #fff;\r
	}\r
.leaflet-control-scale-line:not(:first-child) {\r
	border-top: 2px solid #777;\r
	border-bottom: none;\r
	margin-top: -2px;\r
	}\r
.leaflet-control-scale-line:not(:first-child):not(:last-child) {\r
	border-bottom: 2px solid #777;\r
	}\r
\r
.leaflet-touch .leaflet-control-attribution,\r
.leaflet-touch .leaflet-control-layers,\r
.leaflet-touch .leaflet-bar {\r
	box-shadow: none;\r
	}\r
.leaflet-touch .leaflet-control-layers,\r
.leaflet-touch .leaflet-bar {\r
	border: 2px solid rgba(0,0,0,0.2);\r
	background-clip: padding-box;\r
	}\r
\r
\r
/* popup */\r
\r
.leaflet-popup {\r
	position: absolute;\r
	text-align: center;\r
	margin-bottom: 20px;\r
	}\r
.leaflet-popup-content-wrapper {\r
	padding: 1px;\r
	text-align: left;\r
	border-radius: 12px;\r
	}\r
.leaflet-popup-content {\r
	margin: 13px 24px 13px 20px;\r
	line-height: 1.3;\r
	font-size: 13px;\r
	font-size: 1.08333em;\r
	min-height: 1px;\r
	}\r
.leaflet-popup-content p {\r
	margin: 17px 0;\r
	margin: 1.3em 0;\r
	}\r
.leaflet-popup-tip-container {\r
	width: 40px;\r
	height: 20px;\r
	position: absolute;\r
	left: 50%;\r
	margin-top: -1px;\r
	margin-left: -20px;\r
	overflow: hidden;\r
	pointer-events: none;\r
	}\r
.leaflet-popup-tip {\r
	width: 17px;\r
	height: 17px;\r
	padding: 1px;\r
\r
	margin: -10px auto 0;\r
	pointer-events: auto;\r
\r
	-webkit-transform: rotate(45deg);\r
	   -moz-transform: rotate(45deg);\r
	    -ms-transform: rotate(45deg);\r
	        transform: rotate(45deg);\r
	}\r
.leaflet-popup-content-wrapper,\r
.leaflet-popup-tip {\r
	background: white;\r
	color: #333;\r
	box-shadow: 0 3px 14px rgba(0,0,0,0.4);\r
	}\r
.leaflet-container a.leaflet-popup-close-button {\r
	position: absolute;\r
	top: 0;\r
	right: 0;\r
	border: none;\r
	text-align: center;\r
	width: 24px;\r
	height: 24px;\r
	font: 16px/24px Tahoma, Verdana, sans-serif;\r
	color: #757575;\r
	text-decoration: none;\r
	background: transparent;\r
	}\r
.leaflet-container a.leaflet-popup-close-button:hover,\r
.leaflet-container a.leaflet-popup-close-button:focus {\r
	color: #585858;\r
	}\r
.leaflet-popup-scrolled {\r
	overflow: auto;\r
	}\r
\r
.leaflet-oldie .leaflet-popup-content-wrapper {\r
	-ms-zoom: 1;\r
	}\r
.leaflet-oldie .leaflet-popup-tip {\r
	width: 24px;\r
	margin: 0 auto;\r
\r
	-ms-filter: "progid:DXImageTransform.Microsoft.Matrix(M11=0.70710678, M12=0.70710678, M21=-0.70710678, M22=0.70710678)";\r
	filter: progid:DXImageTransform.Microsoft.Matrix(M11=0.70710678, M12=0.70710678, M21=-0.70710678, M22=0.70710678);\r
	}\r
\r
.leaflet-oldie .leaflet-control-zoom,\r
.leaflet-oldie .leaflet-control-layers,\r
.leaflet-oldie .leaflet-popup-content-wrapper,\r
.leaflet-oldie .leaflet-popup-tip {\r
	border: 1px solid #999;\r
	}\r
\r
\r
/* div icon */\r
\r
.leaflet-div-icon {\r
	background: #fff;\r
	border: 1px solid #666;\r
	}\r
\r
\r
/* Tooltip */\r
/* Base styles for the element that has a tooltip */\r
.leaflet-tooltip {\r
	position: absolute;\r
	padding: 6px;\r
	background-color: #fff;\r
	border: 1px solid #fff;\r
	border-radius: 3px;\r
	color: #222;\r
	white-space: nowrap;\r
	-webkit-user-select: none;\r
	-moz-user-select: none;\r
	-ms-user-select: none;\r
	user-select: none;\r
	pointer-events: none;\r
	box-shadow: 0 1px 3px rgba(0,0,0,0.4);\r
	}\r
.leaflet-tooltip.leaflet-interactive {\r
	cursor: pointer;\r
	pointer-events: auto;\r
	}\r
.leaflet-tooltip-top:before,\r
.leaflet-tooltip-bottom:before,\r
.leaflet-tooltip-left:before,\r
.leaflet-tooltip-right:before {\r
	position: absolute;\r
	pointer-events: none;\r
	border: 6px solid transparent;\r
	background: transparent;\r
	content: "";\r
	}\r
\r
/* Directions */\r
\r
.leaflet-tooltip-bottom {\r
	margin-top: 6px;\r
}\r
.leaflet-tooltip-top {\r
	margin-top: -6px;\r
}\r
.leaflet-tooltip-bottom:before,\r
.leaflet-tooltip-top:before {\r
	left: 50%;\r
	margin-left: -6px;\r
	}\r
.leaflet-tooltip-top:before {\r
	bottom: 0;\r
	margin-bottom: -12px;\r
	border-top-color: #fff;\r
	}\r
.leaflet-tooltip-bottom:before {\r
	top: 0;\r
	margin-top: -12px;\r
	margin-left: -6px;\r
	border-bottom-color: #fff;\r
	}\r
.leaflet-tooltip-left {\r
	margin-left: -6px;\r
}\r
.leaflet-tooltip-right {\r
	margin-left: 6px;\r
}\r
.leaflet-tooltip-left:before,\r
.leaflet-tooltip-right:before {\r
	top: 50%;\r
	margin-top: -6px;\r
	}\r
.leaflet-tooltip-left:before {\r
	right: 0;\r
	margin-right: -12px;\r
	border-left-color: #fff;\r
	}\r
.leaflet-tooltip-right:before {\r
	left: 0;\r
	margin-left: -12px;\r
	border-right-color: #fff;\r
	}\r
\r
/* Printing */\r
\r
@media print {\r
	/* Prevent printers from removing background-images of controls. */\r
	.leaflet-control {\r
		-webkit-print-color-adjust: exact;\r
		print-color-adjust: exact;\r
		}\r
	}\r
`;var Ai=`:host {
  display: block;
  container-type: inline-size;
  color: #e9f0f6;
  font:
    15px/1.5 system-ui,
    -apple-system,
    sans-serif;
  --accent: #80e5cb;
}
* {
  box-sizing: border-box;
}
ha-card {
  display: block;
  background: #121c28;
  border: 1px solid #2a394a;
  border-radius: 22px;
  overflow: hidden;
  color: inherit;
}
:host([fill-screen]) ha-card {
  height: var(--homecircle-screen-height, 100dvh);
  min-height: min-content;
  display: flex;
  flex-direction: column;
}
:host([fill-screen]:not([kiosk])) ha-card {
  min-height: 0;
}
:host(:not([kiosk])) .members {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  align-content: start;
}
:host(:not([kiosk]):not([fill-screen])) .members {
  max-height: clamp(180px, 36dvh, 360px);
}
@media (max-height: 700px) {
  :host([fill-screen]:not([kiosk])) ha-card {
    height: auto;
    min-height: var(--homecircle-screen-height, 100dvh);
  }
  :host([fill-screen]:not([kiosk])) .map-wrap {
    flex: none;
  }
  :host([fill-screen]:not([kiosk])) .members {
    max-height: clamp(180px, 36dvh, 360px);
  }
}
:host([kiosk]) {
  position: fixed;
  inset: 0;
  z-index: 1000;
  width: 100vw;
  height: 100dvh;
  overflow-y: auto;
  background: #121c28;
}
:host([kiosk]) ha-card {
  min-height: 100dvh;
  height: auto;
  border: 0;
  border-radius: 0;
}
:host([fill-screen]) .map-wrap {
  flex: 1;
  min-height: 220px;
  display: flex;
  flex-direction: column;
}
:host([fill-screen]) .map {
  height: auto;
  min-height: 220px;
  flex: 1;
}
header {
  padding: 16px 22px 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.kiosk-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 44px;
  padding: 8px;
}
.kiosk-toggle ha-icon {
  --mdc-icon-size: 24px;
}
:host([fill-screen]) .kiosk-toggle {
  display: inline-flex;
}
.settings-toggle[hidden],
:host([kiosk]) .settings-toggle {
  display: none;
}
.settings-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  padding: 8px;
}
.settings-toggle ha-icon {
  --mdc-icon-size: 20px;
}
h2 {
  margin: 2px 0;
  font-size: 25px;
  font-weight: 650;
  letter-spacing: -0.7px;
}
.eyebrow {
  font-size: 10px;
  letter-spacing: 2.5px;
  color: var(--accent);
  text-transform: uppercase;
}
.subtle {
  color: #a4b5c7;
  font-size: 12px;
}
button {
  font: inherit;
  cursor: pointer;
  color: inherit;
  background: #1d2b3b;
  border: 1px solid #42546a;
  border-radius: 12px;
  min-height: 44px;
  padding: 8px 12px;
}
button:hover {
  background: #2a4052;
}
button:focus-visible,
select:focus-visible,
input:focus-visible {
  outline: 3px solid #80e5cb;
  outline-offset: 3px;
}
button[aria-pressed="true"] {
  border-color: var(--accent);
  background: #203c3c;
}
.overview {
  font-size: 12px;
  white-space: nowrap;
}
.status {
  padding: 0 22px 14px;
  color: #b9c9d8;
  font-size: 12px;
}
.map-visibility-note {
  margin-top: 3px;
  font-size: 11px;
  color: #a4b5c7;
}
:host .kiosk-toggle,
:host .kiosk-toggle[aria-pressed="true"] {
  border-color: #42546a;
  background: transparent;
  color: #a4b5c7;
}
:host .kiosk-toggle:hover {
  background: #1d2b3b;
  color: #e9f0f6;
}
.provider-alerts:not(:empty) {
  margin: 0 14px 14px;
  padding: 10px 12px;
  border: 1px solid #8b6d3d;
  border-radius: 10px;
  background: #392f23;
  color: #f5ddac;
  font-size: 12px;
}
.provider-alert + .provider-alert {
  margin-top: 6px;
}
.map-wrap {
  position: relative;
  margin: 0 14px;
  border: 1px solid #34475b;
  border-radius: 16px;
  overflow: hidden;
}
.map {
  height: 300px;
  background: #192b3d;
  background-image:
    linear-gradient(#ffffff05 1px, transparent 1px),
    linear-gradient(90deg, #ffffff05 1px, transparent 1px);
  background-size: 28px 28px;
  z-index: 0;
}
.map-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px 8px;
  background: #1a2939;
}
.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 500;
  display: flex;
  gap: 0;
  padding: 0;
  border: 1px solid #4b6075;
  border-radius: 999px;
  overflow: hidden;
  background: #121c28;
}
.map-controls[hidden] {
  display: none;
}
.map-controls button {
  flex: 1;
  min-width: 76px;
  min-height: 40px;
  padding: 5.4px 10.8px;
  font-size: 10.8px;
  border: 0;
  border-radius: 0;
  background: #121c28;
}
.map-controls button + button {
  border-left: 1px solid #4b6075;
}
.map-controls button:hover {
  background: #2a4052;
}
.map-controls button[aria-pressed="true"] {
  background: #203c3c;
  color: var(--accent);
}
.map-controls button:focus-visible {
  outline-offset: -3px;
}
.map-note {
  padding: 5px 12px;
  background: #1a2939;
  font-size: 11px;
  color: #b9ccda;
}
.map:empty {
  display: none;
}
.leaflet-control-attribution {
  font-size: 10px !important;
}
.leaflet-control-zoom.leaflet-bar {
  border-radius: 999px;
  overflow: hidden;
  border: 2px solid #4b6075;
  background: #121c28;
}
.leaflet-control-zoom button {
  display: block;
  padding: 0;
  border: 0;
  border-radius: 0;
  font:
    bold 22px/44px Arial,
    Helvetica,
    sans-serif;
}
.leaflet-control-zoom button:first-child {
  border-bottom: 1px solid #4b6075;
}
.leaflet-control-zoom button:disabled {
  cursor: default;
  opacity: 0.5;
}
.leaflet-control-zoom button {
  width: 44px !important;
  height: 44px !important;
  line-height: 44px !important;
  background: #121c28 !important;
  color: #e9f0f6 !important;
}
.marker {
  border: 0;
  background: none;
}
.marker button {
  width: 54px;
  height: 68px;
  min-height: 68px;
  padding: 0;
  border: 0;
  border-radius: 0;
  color: #122331;
  background: transparent;
  font-weight: 750;
  display: grid;
  place-items: start center;
  position: relative;
}
.marker button::before {
  content: "";
  position: absolute;
  inset: 0 auto auto 0;
  width: 54px;
  height: 54px;
  box-sizing: border-box;
  border-radius: 50%;
  background: #edfdf7;
  border: 3px solid #fff;
  box-shadow: 0 3px 14px #0008;
}
.marker button::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  border-left: 12px solid transparent;
  border-right: 12px solid transparent;
  border-top: 19px solid #fff;
  filter: drop-shadow(0 2px 2px #0008);
}
.marker button > .marker-avatar {
  width: 42px;
  height: 42px;
  margin-top: 6px;
  z-index: 1;
}
.marker .group {
  width: 90px;
  height: 108px;
  min-height: 108px;
}
.marker .group::before {
  width: 90px;
  height: 90px;
}
.marker .group::after {
  border-left-width: 15px;
  border-right-width: 15px;
  border-top-width: 24px;
}
.marker .group > .marker-portraits {
  margin-top: 5px;
  z-index: 1;
}
.marker-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #88e4ce;
  color: #122331;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  font-size: 11px;
  line-height: 1;
  border: 2px solid #fff;
  box-shadow: 0 2px 5px #0006;
}
.marker-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.marker-portraits {
  position: relative;
  display: block;
  width: 80px;
  height: 80px;
}
.marker-portraits .marker-avatar {
  position: absolute;
  width: 43px;
  height: 43px;
  font-size: 12px;
}
.marker-portraits .marker-avatar:nth-child(1) {
  left: 0;
  top: 0;
}
.marker-portraits .marker-avatar:nth-child(2) {
  right: 0;
  top: 0;
}
.marker-portraits .marker-avatar:nth-child(3) {
  left: 0;
  bottom: 0;
}
.marker-portraits .marker-avatar:nth-child(4) {
  right: 0;
  bottom: 0;
}
.marker-portraits.count-2 .marker-avatar {
  top: 18px;
}
.marker-portraits.count-3 .marker-avatar:nth-child(1) {
  left: 18px;
  top: 0;
}
.marker-portraits.count-3 .marker-avatar:nth-child(2) {
  left: 0;
  right: auto;
  top: auto;
  bottom: 0;
}
.marker-portraits.count-3 .marker-avatar:nth-child(3) {
  left: auto;
  right: 0;
  bottom: 0;
}
.marker-overflow {
  position: absolute;
  right: -5px;
  bottom: -5px;
  min-width: 27px;
  height: 27px;
  padding: 0 3px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #253e54;
  border: 2px solid #fff;
  color: #fff;
  font-size: 10px;
}
.categories {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 16px 18px 8px;
}
.category {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 9px 3px;
}
.count {
  font-size: 24px;
  line-height: 1.2;
  font-weight: 650;
}
.label {
  font-size: 11px;
  color: #bacbdb;
}
.members {
  padding: 4px 18px 18px;
  display: grid;
  grid-auto-rows: max-content;
  gap: 8px;
}
.member-entry {
  position: relative;
  min-width: 0;
}
.member {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: start;
  text-align: left;
  gap: 10px;
  background: #172331;
  padding: 10px 56px 10px 12px;
  touch-action: pan-y;
}
.member > .avatar {
  align-self: center;
}
.member-details-button {
  display: grid;
  place-items: center;
  position: absolute;
  top: 10px;
  right: 8px;
  width: 40px;
  min-height: 40px;
  padding: 0;
  border-radius: 50%;
  background: #263947;
  color: #c8e6ec;
  line-height: 1;
}
.member-details-button svg {
  display: block;
  width: 24px;
  height: 24px;
  pointer-events: none;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #2a424e;
  color: var(--accent);
  display: grid;
  place-items: center;
  font-weight: 650;
  position: relative;
  overflow: hidden;
}
.avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.name {
  font-size: 15px;
  font-weight: 650;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.member-heading {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 4px 8px;
}
.member-facts,
.report-lines {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 9px;
  margin-top: 4px;
}
.location-since,
.place,
.report-part,
.driving-note {
  font-size: 11.5px;
  color: #a4b6c7;
}
.place {
  color: #c2d2de;
}
.address {
  flex-basis: 100%;
  overflow-wrap: anywhere;
}
.report-part.source {
  color: #b6d9e7;
  font-weight: 600;
}
.battery {
  color: #c3d9df;
  background: #263947;
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 10.5px;
  white-space: nowrap;
}
.battery.low {
  color: #ffe4ac;
  background: #5d4524;
  font-weight: 650;
}
.battery.critical {
  color: #ffe0dc;
  background: #65342f;
}
.driving-note {
  display: block;
  margin-top: 5px;
  color: #efd088;
}
.report-part.unknown {
  color: #d2e2ec;
  font-weight: 550;
}
.report-part.unverified {
  color: #ffe4ac;
  font-weight: 650;
}
.report-part.stale {
  color: #d6c5a1;
  background: #34352f;
  border-radius: 9px;
  padding: 1px 7px;
  font-weight: 550;
}
.badge {
  font-size: 11.5px;
  padding: 4px 9px;
  border-radius: 16px;
  background: #243746;
  color: #badddf;
  white-space: nowrap;
  flex: none;
}
.badge.away {
  color: #b9cfff;
}
.badge.driving {
  color: #efd088;
}
.badge.unavailable {
  color: #c5c9ce;
}
.expanded {
  padding: 10px 18px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.expanded:empty {
  display: none;
}
.empty {
  padding: 28px 22px;
  color: #b9c9d8;
}
.editor {
  display: grid;
  gap: 18px;
  padding: 14px;
  color: var(--primary-text-color, #172331);
  font: 14px system-ui;
}
.editor label {
  display: grid;
  gap: 7px;
}
.editor input[type="text"],
.editor select {
  font: inherit;
  min-height: 44px;
  border: 1px solid #8193a2;
  border-radius: 8px;
  padding: 8px;
  background: var(--card-background-color, white);
  color: inherit;
}
.editor .check {
  display: flex;
  align-items: center;
  gap: 10px;
}
.editor input[type="checkbox"] {
  width: 20px;
  height: 20px;
}
.editor p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}
.editor fieldset {
  border: 1px solid #8193a2;
  border-radius: 8px;
  display: grid;
  gap: 10px;
}
.editor a {
  color: var(--primary-color, #167681);
}
@container (max-width: 400px) {
  header {
    padding: 16px 16px 12px;
  }
  h2 {
    font-size: 23px;
  }
  .map {
    height: 220px;
  }
  .categories {
    padding: 12px 12px 6px;
    gap: 5px;
  }
  .members {
    padding: 4px 12px 12px;
  }
  .member {
    gap: 8px;
    padding: 10px 54px 10px 10px;
    grid-template-columns: 36px minmax(0, 1fr);
  }
  .member-heading {
    display: block;
  }
  .member-heading .badge {
    display: inline-block;
    margin-top: 4px;
  }
  .avatar {
    width: 34px;
    height: 36px;
  }
  .badge {
    padding: 3px 6px;
    font-size: 10px;
  }
}

@container (max-width: 359px) {
  .categories {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .category {
    padding: 6px 3px;
  }
}

@container (min-width: 800px) {
  .members {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .map {
    height: 380px;
  }
}
.leaflet-control-zoom a:focus-visible,
.leaflet-control-zoom button:focus-visible {
  outline: 3px solid #80e5cb;
  outline-offset: -3px;
}

.member.attention {
  border-left: 4px solid #f2c66d;
}

.location-feedback:not(:empty) {
  margin: 0 22px 12px;
  color: #b9ccda;
  font-size: 12px;
}

/* The explicit height wins over automatic kiosk and responsive map sizing. */
:host .map-wrap.resized {
  flex: none;
}
:host .map-wrap.resized .map {
  height: var(--map-height);
  flex: none;
}
.map-resize {
  position: relative;
  height: 12px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a2939;
  cursor: ns-resize;
  touch-action: none;
  user-select: none;
}
/* Extend the central hit area without adding another blank footer row. */
.map-resize::before {
  content: "";
  position: absolute;
  width: 96px;
  height: 24px;
  bottom: 0;
}
.map-resize::after {
  content: "";
  width: 48px;
  height: 4px;
  border-radius: 8px;
  background: #7d94aa;
}
.map-resize:hover::after {
  background: var(--accent);
}
.map-resize:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -3px;
}

.family-refresh {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 0 22px 10px;
}
.family-refresh[hidden] {
  display: none;
}
.family-refresh-button {
  min-height: 44px;
  border: 1px solid #64748b;
  border-radius: 22px;
  background: #121c28;
  color: white;
  padding: 8px 16px;
  cursor: pointer;
}
.family-refresh-button:disabled {
  opacity: 0.65;
  cursor: default;
}
.family-refresh-button:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 2px;
}
.family-refresh-feedback {
  flex: 1 1 250px;
  color: var(--secondary-text-color, #94a3b8);
  font-size: 13px;
  line-height: 1.5;
}

.radar-controls {
  position: absolute;
  top: 58px;
  right: 10px;
  z-index: 500;
  text-align: right;
}
.radar-options {
  margin-top: 5px;
  width: 180px;
  padding: 9px;
  border: 1px solid #4b6075;
  border-radius: 12px;
  background: #121c28;
  font-size: 11px;
}
.radar-options label {
  display: flex;
  align-items: center;
  gap: 5px;
}
.radar-options input {
  width: 76px;
  accent-color: var(--accent);
}
.radar-legend {
  margin-top: 6px;
  padding-top: 7px;
  background: linear-gradient(to right, #32b44a, #ead647, #e1682c, #b22aaa)
    top / 100% 4px no-repeat;
  text-align: center;
}
.radar-note {
  padding: 5px 12px;
  font-size: 11px;
  color: #b9ccda;
}
.radar-controls[hidden],
.radar-options[hidden],
.radar-note[hidden] {
  display: none;
}

.radar-playback {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  color: #b9ccda;
  font-size: 11px;
}
.radar-playback button {
  min-height: 32px;
  min-width: 36px;
  padding: 3px 10px;
  border: 1px solid #4b6075;
  border-radius: 999px;
  background: #121c28;
}
.radar-playback button[aria-pressed="true"] {
  color: var(--accent);
}
.radar-playback[hidden] {
  display: none;
}

.radar-playback {
  flex-wrap: wrap;
}
.radar-playback select {
  border: 1px solid #4b6075;
  border-radius: 999px;
  padding: 5px 8px;
  background: #121c28;
  color: inherit;
  font: inherit;
}

.map-recenter {
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: 48px;
  height: 48px;
  padding: 0;
  background: #121c28;
  color: #e9f0f6;
  border: 2px solid #4b6075;
  border-radius: 50%;
}
.map-recenter svg {
  width: 22px;
  height: 22px;
  display: block;
}
.map-recenter:disabled {
  cursor: default;
  opacity: 0.5;
}
.connection-warning {
  color: #ffd27a;
}

.location-since {
  margin-top: 4px;
}

.city-credit {
  padding: 0 18px 12px;
  font-size: 11px;
}
.city-credit a {
  color: #9bb1c3;
}
`;var Jn={domain:"homecircle",name:"HomeCircle",codeowners:["@jmhjr"],config_flow:!0,dependencies:["frontend","http","image_upload","lovelace","person","websocket_api","zone"],documentation:"https://github.com/jmhjr/HomeCircle",integration_type:"service",iot_class:"calculated",issue_tracker:"https://github.com/jmhjr/HomeCircle/issues",requirements:["life360==7.2.0","protobuf>=6.32.0,<8.0.0","anisette==1.2.4","unicorn==2.1.4","srp==1.0.22","beautifulsoup4==4.13.3"],single_config_entry:!0,version:"0.1.0-beta.19"};function Yr(l,s,a=1,d=0,p=0){let h=Math.max(l,s)/Math.max(.5,a),f=g=>(Math.max(-100,Math.min(100,g))+100)/200;return{x:(l-h)*f(d),y:(s-h)*f(p),side:h}}function Qn(l){let s=document.createElement("div");s.hidden=!0;let a=document.createElement("p");a.textContent="Drag the picture or use the sliders to position it. The circle shows how it will appear on the card.";let d=document.createElement("canvas");d.width=d.height=512,d.setAttribute("aria-label","Cropped picture preview"),d.style.cssText="display:block;width:min(256px,100%);aspect-ratio:1;margin:12px auto;border-radius:50%;touch-action:none;cursor:grab";let p={};for(let[w,z,q,D,A]of[["Zoom",.5,8,.05,1],["Horizontal position",-100,100,1,0],["Vertical position",-100,100,1,0]]){let X=document.createElement("label");X.textContent=w,X.style.cssText="display:block;margin:12px 0";let F=document.createElement("input");F.type="range",Object.assign(F,{min:String(z),max:String(q),step:String(D),value:String(A)}),F.setAttribute("aria-label",w),F.style.cssText="display:block;width:100%",F.addEventListener("input",_),p[w]=F,X.append(F),s.append(X)}let h=null,f=0,g=null,P=()=>Yr(h.naturalWidth,h.naturalHeight,Number(p.Zoom.value),Number(p["Horizontal position"].value),Number(p["Vertical position"].value));function _(){if(!h)return;let w=d.getContext("2d");if(!w)throw new Error("Picture editing is unavailable");let z=P();w.fillStyle="white",w.fillRect(0,0,512,512),w.drawImage(h,z.x,z.y,z.side,z.side,0,0,512,512)}let C=document.createElement("button");C.type="button",C.textContent="Reset crop",C.addEventListener("click",()=>{p.Zoom.value="1",p["Horizontal position"].value=p["Vertical position"].value="0",_()}),d.addEventListener("pointerdown",w=>{h&&(g={x:w.clientX,y:w.clientY},d.setPointerCapture(w.pointerId))}),d.addEventListener("pointermove",w=>{if(!g||!h)return;let z=P(),q=d.getBoundingClientRect().width;if(q){for(let[D,A,X]of[["Horizontal position",w.clientX-g.x,h.naturalWidth-z.side],["Vertical position",w.clientY-g.y,h.naturalHeight-z.side]])X!==0&&(p[D].value=String(Math.max(-100,Math.min(100,Number(p[D].value)-A*z.side/q/X*200))));g={x:w.clientX,y:w.clientY},_()}});let j=()=>{g=null};d.addEventListener("pointerup",j),d.addEventListener("pointercancel",j),s.prepend(a,d),s.append(C);function Z(){f++,h=null,s.hidden=!0,g=null,l(!1)}return{panel:s,get active(){return!!h},clear:Z,async load(w){Z();let z=f,q=await new Promise((A,X)=>{let F=new FileReader;F.onload=()=>A(F.result),F.onerror=()=>X(new Error("Cannot read picture")),F.readAsDataURL(w)}),D=await new Promise((A,X)=>{let F=new Image;F.onload=()=>A(F),F.onerror=()=>X(new Error("Cannot decode picture")),F.src=q});z!==f||!s.isConnected||(h=D,p.Zoom.value="1",p["Horizontal position"].value=p["Vertical position"].value="0",_(),s.hidden=!1,l(!0))},async file(){if(!h)throw new Error("No picture selected");_();let w=await new Promise(z=>d.toBlob(z,"image/jpeg",.92));if(!w)throw new Error("Cannot crop picture");return new File([w],"homecircle-picture.jpg",{type:"image/jpeg"})}}}var ee="config/config_entries/options/flow";function eo(l){let s={};for(let a of l||[])if(a.description?.suggested_value!=null)s[a.name]=a.description.suggested_value;else if(Object.hasOwn(a,"default"))s[a.name]=a.default;else if(a.type==="expandable"){let d=eo(a.schema);(a.required||Object.keys(d).length)&&(s[a.name]=d)}else if(a.required&&a.selector?.select?.options?.length){let d=a.selector.select,p=d.options[0],h=typeof p=="string"?p:p.value;s[a.name]=d.multiple?[h]:h}else a.required&&a.selector?.boolean?s[a.name]=!1:a.required&&a.selector?.entity&&(s[a.name]=a.selector.entity.multiple?[]:"");return s}function to(l,s,a,d){return l.localize?.(s,d)||a}function Xr(l,s){s=s.replaceAll("**","").replace(/\\([\\`*_{}\[\]<>])/g,"$1");let a="[Home Assistant People settings](/config/person)",d=s.indexOf(a);if(d<0){l.textContent=s;return}l.append(document.createTextNode(s.slice(0,d)));let p=document.createElement("a");p.href="/config/person",p.textContent="Home Assistant People settings",l.append(p,document.createTextNode(s.slice(d+a.length)))}async function je(l,s,a=null,d=null){if(!s?.user?.is_admin)return;let p=document.querySelector("home-assistant")?.shadowRoot||document.body;if(p.querySelector("dialog.homecircle-settings"))return;let h=document.createElement("dialog");h.className="homecircle-settings",h.setAttribute("aria-label","HomeCircle settings"),h.innerHTML=`<style>
    dialog.homecircle-settings { width: min(620px, calc(100vw - 32px)); max-height: min(85vh, 850px); padding: 0; border: 0; border-radius: 22px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #222); box-shadow: 0 20px 70px #0007; }
    dialog.homecircle-settings::backdrop { background: #0009; }
    .homecircle-settings * { box-sizing: border-box; }
    .homecircle-settings header { display: flex; align-items: center; gap: 12px; padding: 20px 24px 12px; border-bottom: 1px solid var(--divider-color, #ddd); }
    .homecircle-settings h2 { flex: 1; margin: 0; font: 600 20px/1.3 system-ui, sans-serif; }
    .homecircle-settings .heading { flex: 1; min-width: 0; }
    .homecircle-settings .version { margin-top: 4px; color: var(--secondary-text-color, #666); font: 12px/1.4 system-ui, sans-serif; }
    .homecircle-settings button { font: inherit; cursor: pointer; }
    .homecircle-settings .close { border: 0; background: transparent; color: inherit; font-size: 25px; line-height: 1; min-width: 36px; min-height: 36px; }
    .homecircle-settings .body { padding: 16px 24px 22px; overflow-y: auto; max-height: calc(min(85vh, 850px) - 75px); }
    .homecircle-settings .choice { display: block; width: 100%; padding: 15px 12px; margin: 4px 0; border: 0; border-radius: 10px; background: transparent; color: inherit; text-align: left; }
    .homecircle-settings .choice[hidden] { display: none; }
    .homecircle-settings .choice:hover, .homecircle-settings .choice:focus-visible { background: var(--secondary-background-color, #eee); }
    .homecircle-settings .choice::after { content: "\u203A"; float: right; font-size: 22px; line-height: 18px; }
    .homecircle-settings .description { margin: 0 0 18px; color: var(--secondary-text-color, #666); white-space: pre-line; }
    .homecircle-settings .settings-label { margin: 20px 0 8px; font: 600 15px/1.4 system-ui, sans-serif; }
    .homecircle-settings ha-form { display: block; width: 100%; }
    .homecircle-settings .error { color: var(--error-color, #b3261e); }
    .homecircle-settings .actions { display: flex; justify-content: flex-end; gap: 10px; padding-top: 18px; }
    .homecircle-settings .actions button { padding: 9px 15px; border-radius: 9px; border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color, #fff); color: inherit; }
    .homecircle-settings .actions .primary { background: var(--primary-color, #03a9f4); color: white; border-color: transparent; }
  </style><header><div class="heading"><h2></h2><div class="version"></div></div><button type="button" class="close" aria-label="Close">\xD7</button></header><div class="body"></div>`,p.append(h),h.querySelector(".version").textContent=l._integrationVersion?`Version ${l._integrationVersion}`:"";let f=h.querySelector("h2"),g=h.querySelector(".body"),P,_=!1,C=a,j=new Set,Z=b=>{!b?.flow_id||["create_entry","abort"].includes(b.type)||j.has(b.flow_id)||(j.add(b.flow_id),s.callApi("DELETE",`${ee}/${b.flow_id}`).catch(()=>{}))},w=b=>h.isConnected?(P=b,!0):(Z(b),!1),z,q=()=>h.close();h.querySelector(".close").addEventListener("click",q),h.addEventListener("close",()=>{clearTimeout(z),Z(P),h.remove(),l._settingsButton?.focus()}),h.addEventListener("click",b=>{b.target.closest?.('a[href="/config/person"]')&&q()}),h.showModal();let D=(b,H=!1)=>{f.textContent="HomeCircle settings",g.replaceChildren();let T=document.createElement("p");T.className=H?"error":"description",T.textContent=b,g.append(T)},A=(b,H,T=P?.description_placeholders)=>to(l._hass||s,`component.homecircle.options.${b}`,H,T),X=async b=>{if(!(_||!P||!h.isConnected)){_=!0;try{let H=await s.callApi("POST",`${ee}/${P.flow_id}`,b);ct(H)}catch{D("Could not update HomeCircle settings. Close this dialog and try again.",!0)}finally{_=!1}}},F=(b,H,T=!1)=>{let M=document.createElement("button");return M.type="button",M.textContent=b,T&&(M.className="primary"),M.addEventListener("click",H),M},yt=async b=>{if(!(_||!h.isConnected)){_=!0;try{let H=await s.callWS({type:"config_entries/get",domain:"homecircle"});if(!h.isConnected||!H?.length)return;let T=P,M=await s.callApi("POST",ee,{handler:H[0].entry_id});if(Z(T),!w(M))return;ct(b?await s.callApi("POST",`${ee}/${M.flow_id}`,{next_step_id:b}):M)}catch{h.isConnected&&D("Could not return to settings choices.",!0)}finally{_=!1}}},ct=b=>{if(w(b)){if(clearTimeout(z),g.replaceChildren(),b.type==="progress"||b.type==="progress_done"){D(A(`progress.${b.progress_action}`,"Connecting to Apple\u2026")),z=setTimeout(()=>{P!==b||!h.isConnected||_||(_=!0,s.callApi("GET",`${ee}/${b.flow_id}`).then(H=>{h.isConnected&&P===b&&ct(H)}).catch(()=>{h.isConnected&&D("Could not check Apple setup progress. Close and try again.",!0)}).finally(()=>{_=!1}))},b.type==="progress_done"?0:2e3);return}if(b.type==="create_entry"){q(),l._load();return}if(b.type==="abort"){D(A(`abort.${b.reason}`,"Setup was stopped."));return}if(b.type==="menu"){f.textContent=A(`step.${b.step_id}.title`,"What would you like to change?");let H=A(`step.${b.step_id}.description`,"");if(H){let M=document.createElement("p");M.className="description",M.textContent=H.replaceAll("**",""),g.append(M)}if(b.step_id==="init"&&!a&&l._radarController){let M=document.createElement("label");M.style.cssText="display:flex;align-items:center;gap:10px;padding:12px";let y=document.createElement("input");y.type="checkbox",y.checked=l._radarController.showControls,y.addEventListener("change",()=>l._radarController.setShowControls(y.checked)),M.append(y,document.createTextNode("Show radar opacity and color guide"));let J=document.createElement("p");J.className="description",J.textContent="For this browser. Controls appear on the map when Radar is on.",g.append(M,J)}let T=Array.isArray(b.menu_options)?b.menu_options.map(M=>[M,A(`step.${b.step_id}.menu_options.${M}`,M)]):Object.entries(b.menu_options);for(let[M,y]of T){let J=F(y,()=>X({next_step_id:M}));J.className="choice",g.append(J)}return}if(b.type==="form"){f.textContent=A(`step.${b.step_id}.title`,"HomeCircle settings");let H=A(`step.${b.step_id}.description`,"");if(H){let E=document.createElement("p");E.className="description",Xr(E,H),g.append(E)}if(b.errors?.base){let E=document.createElement("p");E.className="error",E.textContent=A(`error.${b.errors.base}`,b.errors.base),g.append(E)}let T=document.createElement("ha-form"),M=b.step_id==="tracker_member_choice",y=b.step_id==="findmy_select",J=b.step_id==="import_place_select"||y,Q=y?"items":"places",Ut=b.step_id==="import_place_edit",lt=b.step_id==="tracker_picture",wt=!1,N=async()=>!0,Me=b.data_schema?.find(E=>E.name==="setting");T.hass=l._hass||s,T.schema=J||lt?[]:M?b.data_schema?.filter(E=>E.name==="member")||[]:Ut?b.data_schema?.filter(E=>E.name!=="skip")||[]:b.data_schema||[];let I=T.schema[0]?.selector?.select?.options||[],it=M&&I.some(E=>E.value===C);T.data=M?it?{member:C}:{}:eo(J||lt?b.data_schema:T.schema),T.error=b.errors||{},T.context={handler:b.handler,domain:"homecircle"},T.computeLabel=E=>A(`step.${b.step_id}.data.${E.name}`,b.step_id==="findmy_types"&&E.name.startsWith("type_")?`Item ${Number(E.name.slice(5))+1} type`:E.name),T.computeHelper=E=>A(`step.${b.step_id}.data_description.${E.name}`,""),T.computeError=E=>A(`error.${E}`,E),T.localizeValue=E=>to(l._hass||s,`component.homecircle.selector.${E}`,E);let dt=document.createElement("div");dt.hidden=!T.data?.member;let gt=new Set((b.description_placeholders?.removable_members||"").split(",").filter(Boolean)),rt=new Set((b.description_placeholders?.picture_members||"").split(",").filter(Boolean)),K,U;if(M){let E=document.createElement("h3");E.className="settings-label",E.textContent=A(`step.${b.step_id}.data.setting`,"Available settings"),dt.append(E);for(let nt of Me?.selector?.select?.options||[]){let ot=F(nt.label,()=>X({member:T.data.member,setting:nt.value}));ot.className="choice",nt.value==="remove"&&(ot.hidden=!gt.has(T.data?.member)),nt.value==="picture"&&(ot.hidden=!rt.has(T.data?.member),K=ot),dt.append(ot),nt.value==="remove"&&(U=ot)}}if(T.addEventListener("value-changed",E=>{T.data=E.detail.value,M&&(C=T.data?.member,dt.hidden=!C),K&&(K.hidden=!rt.has(T.data?.member)),U&&(U.hidden=!gt.has(T.data?.member))}),g.append(T),lt){let E=document.createElement("div");E.className="tracker-picture";let nt=document.createElement("img");nt.alt="Custom tracker picture preview",nt.style.cssText="display:block;width:128px;height:128px;object-fit:cover;border-radius:50%;margin:16px auto";let ot=document.createElement("p");ot.setAttribute("aria-live","polite");let At=document.createElement("label");At.textContent="Upload picture (JPG, PNG, or GIF; up to 10 MB)";let tt=document.createElement("input");tt.type="file",tt.accept="image/jpeg,image/png,image/gif",tt.setAttribute("aria-label","Upload picture"),tt.style.cssText="display:block;margin:12px 0;width:100%",At.append(tt);let ut=Qn(G=>{nt.style.display=G||nt.hidden||ut.active?"none":"block"});h.addEventListener("close",()=>ut.clear(),{once:!0});let Lt=()=>{let G=T.data.picture_id||"";nt.hidden=!/^[0-9a-f]{32}$/.test(G),nt.style.display=nt.hidden||ut.active?"none":"block",nt.hidden?nt.removeAttribute("src"):nt.src=`/api/image/serve/${G}/512x512`,Ct.disabled=!G||wt},Ct=F("Remove picture",()=>{ut.clear(),T.data={...T.data,picture_id:""},ot.textContent="Save to restore the tracker\u2019s original picture or initials.",Lt()});tt.addEventListener("change",async()=>{let G=tt.files?.[0];if(G){if(!["image/jpeg","image/png","image/gif"].includes(G.type)||G.size>10*1024*1024){ot.textContent="Choose a JPG, PNG, or GIF picture no larger than 10 MB.",tt.value="";return}wt=!0,tt.disabled=!0,Ct.disabled=!0,ot.textContent="Preparing picture\u2026";try{await ut.load(G),ot.textContent="Adjust the crop and zoom, then save your picture."}catch{ut.clear(),ot.textContent="Could not open this picture. Try another JPG, PNG, or GIF file."}finally{wt=!1,tt.disabled=!1,tt.value="",Lt()}}}),N=async()=>{if(wt)return!1;if(!ut.active)return!0;wt=!0,tt.disabled=!0,Ct.disabled=!0,ot.textContent="Uploading cropped picture\u2026";try{let G=new FormData;G.append("file",await ut.file());let Et=await(l._hass||s).fetchWithAuth("/api/image/upload",{method:"POST",body:G});if(!Et.ok)throw new Error("Upload failed");let Tt=await Et.json();if(!/^[0-9a-f]{32}$/.test(Tt.id))throw new Error("Invalid picture response");return!h.isConnected||_||P!==b?!1:(T.data={...T.data,picture_id:Tt.id},ut.clear(),!0)}catch{return ot.textContent="Could not upload this picture. Your crop is kept; try saving again.",!1}finally{wt=!1,tt.disabled=!1,Lt()}},Lt(),E.append(nt,At,ut.panel,Ct,ot),g.append(E)}if(J){let E=b.data_schema?.find(G=>G.name===Q)?.selector?.select?.options||[],nt=document.createElement("div");nt.className="place-selection";let ot=document.createElement("div");ot.className="actions";let At=document.createElement("p");At.setAttribute("aria-live","polite");let tt=document.createElement("input");tt.type="search",tt.placeholder=y?"Search Find My items":"Search saved places",tt.setAttribute("aria-label",y?"Search Find My items":"Search saved places"),tt.style.cssText="width:100%;padding:10px;margin:12px 0;font:inherit";let ut=document.createElement("div");ut.style.cssText="max-height:340px;overflow-y:auto;border:1px solid var(--divider-color,#ddd);border-radius:10px",ut.setAttribute("role","group"),ut.setAttribute("aria-label",y?"Find My items":"Saved places");let Lt=[],Ct=()=>{T.data={...T.data,[Q]:Lt.filter(({check:G})=>G.checked).map(({value:G})=>G)},At.textContent=`${T.data[Q].length} of ${E.length} ${y?"items":"places"} selected`};ot.append(F("Select all",()=>{for(let{check:G}of Lt)G.checked=!0;Ct()}),F("Clear selection",()=>{for(let{check:G}of Lt)G.checked=!1;Ct()}));for(let G of E){let Et=typeof G=="string"?G:G.value,Tt=(typeof G=="string"?G:G.label).replace(/ · [\d.]+ m(?= · |$)/,""),ne=document.createElement("label");ne.style.cssText="display:flex;align-items:center;gap:12px;padding:12px;cursor:pointer";let $t=document.createElement("input");$t.type="checkbox",$t.checked=(T.data[Q]||[]).includes(Et),$t.addEventListener("change",Ct),ne.append($t,document.createTextNode(Tt)),ut.append(ne),Lt.push({check:$t,value:Et,row:ne,labelText:Tt})}tt.addEventListener("input",()=>{let G=tt.value.toLocaleLowerCase().trim();for(let{row:Et,labelText:Tt}of Lt)Et.style.display=Tt.toLocaleLowerCase().includes(G)?"flex":"none"}),Ct(),nt.append(ot,At,tt,ut),g.append(nt)}M&&g.append(dt);let kt=document.createElement("div");kt.className="actions",kt.append(F("Back",()=>{if(M&&a&&d){q(),d(C||a);return}yt(b.step_id==="add_tracker_assign"?"add_tracker_choice":C&&["remove_tracker_choice","member","supporting"].includes(b.step_id)?"tracker_member_choice":void 0)}),...Ut?[F("Skip this place",()=>X({skip:!0}))]:[],...M?[]:[F(lt?"Save picture":"Continue",async()=>{wt||(!lt||await N())&&X(T.data||{})},!0)]),g.append(kt);return}D("Continue this setup from the HomeCircle integration page.",!0)}};D("Opening settings\u2026");try{let b=await s.callWS({type:"config_entries/get",domain:"homecircle"});if(!h.isConnected)return;if(!b?.length){D("Add the HomeCircle integration before changing settings.",!0);return}if(await Promise.all([s.loadFragmentTranslation?.("config"),s.loadBackendTranslation?.("options","homecircle"),s.loadBackendTranslation?.("selector","homecircle")]),!h.isConnected)return;let H=await s.callApi("POST",ee,{handler:b[0].entry_id});if(!w(H))return;ct(a?await s.callApi("POST",`${ee}/${H.flow_id}`,{next_step_id:"tracker_member_choice"}):H)}catch{h.isConnected&&D("Could not open HomeCircle settings. Try again in a moment.",!0)}}var Ce=["home","away","driving","unavailable"],jt={home:"Home",away:"Away",driving:"Driving",unavailable:"Unavailable",overview:"Everyone",items:"Items"},Jr={selection_needed:"trackers are ready; open HomeCircle Options to choose a tracker from this account",starting:"connecting to the tracker service",discovering:"finding trackers",partial:"some trackers could not be updated; check HomeCircle Options if this continues",auth_required:"sign-in needs attention; open Home Assistant Repairs",rate_limited:"temporarily rate limited; HomeCircle will retry",network_error:"connection failed; HomeCircle will retry",api_error:"tracker request failed; check HomeCircle Options if this continues",unexpected_response:"tracker service response changed; check HomeCircle diagnostics"};function no(l){let s=Jr[l?.state];return s&&typeof l.name=="string"?`${l.name}: ${s}.`:null}function Bi(l,s=[]){return(l?.members||[]).filter(a=>!s.includes(a.id))}function oo(l,s,a){let p=["overview","items",...Ce].includes(s)?new Set(a?.[s]||[]):new Set([s]);return l.filter(h=>h.focusable&&h.location&&(h.map_visible!==!1||s!=="overview")&&p.has(h.id))}var Qr=new Set("Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia|Puerto Rico".toLowerCase().split("|")),ro=new Set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split(" "));function Ei(l){let s=l.replace(/\s+\d{5}(?:-\d{4})?$/,"").trim();return Qr.has(s.toLowerCase())||ro.has(s.toUpperCase())}function ts(l,s=null){if(typeof l!="string")return null;let a=l.split(",").map(g=>g.trim()).filter(Boolean);if(typeof s=="string"&&s){if(a.length===1&&a[0]===s)return s;if(a[1]===s)return`${a[0]}, ${s}`}let d=new Set(["new york","washington"]);if(!a.length||Ei(a[0])&&!d.has(a[0].toLowerCase()))return null;let p=a[0],h=a[1];if(!h||Ei(h)&&!d.has(h.toLowerCase())&&!(a.length>2&&Ei(a[2])))return p;h=h.replace(/\s+\d{5}(?:-\d{4})?$/,"").trim();let f=h.match(/^(.*)\s+([A-Z]{2})$/);return f&&ro.has(f[2])&&(h=f[1].trim()),h?`${p}, ${h}`:p}function so(l){if(l.place||!l.focusable||!l.location)return null;let s=ts(l.reported_address,l.reported_city);return typeof s!="string"||!s.trim()?["away","driving"].includes(l.presence)?"Address unavailable":null:l.location.evidence?.freshness==="fresh"?`At ${s}`:`Last reported: ${s}`}function ao(l,s={},a,d=Date.now()){let p={text:"Since unknown",title:"No reliable arrival time for this location."};if(!l.place&&!(l.arrival?.source==="tracker"&&l.reported_address)||!l.focusable||!l.location||l.presence==="driving")return p;let h;if(l.arrival)h=typeof l.arrival.since=="string"?Date.parse(l.arrival.since):NaN;else{let g=s[l.id],P=l.place.trim().toLowerCase(),_=typeof g?.state=="string"?g.state.trim().toLowerCase():"";if(!_||["unknown","unavailable","not_home"].includes(_)||!(_===P||_==="home"&&l.primary_home===!0)||l.issues?.includes("gps_inside_zone_ha_pending")||(h=typeof g.last_changed=="string"&&/(?:Z|[+-]\d{2}:\d{2})$/.test(g.last_changed)?Date.parse(g.last_changed):NaN,!Number.isFinite(h)||h>d))return p;let C=(l.activity?.events||[]).filter(Z=>Z.kind==="started").map(Z=>Date.parse(Z.observed_at)).filter(Number.isFinite),j=C.length?Math.max(...C):NaN;if(!Number.isFinite(j)||h<=j+5e3)return p}if(!Number.isFinite(h)||h>d)return p;let f=a?{timeZone:a}:{};try{let g=C=>new Intl.DateTimeFormat(void 0,{...f,year:"numeric",month:"numeric",day:"numeric"}).format(C),P=g(h)===g(d);return{text:`Since ${new Intl.DateTimeFormat(void 0,{...f,hour:"numeric",minute:"2-digit",...P?{}:{month:"short",day:"numeric",year:"numeric"}}).format(h)}`,title:(l.arrival?.source==="tracker"?"Arrival time reported by the selected tracker.":"HomeCircle observed this arrival; detection may follow the actual arrival.")+(l.arrival?.continuity_unconfirmed?" Saved across an observation gap; uninterrupted presence is unconfirmed.":"")+(l.arrival?.persistent===!1?" Persistence is unavailable; this time may be lost after restart.":"")}}catch{return p}}function io(l,s){let a=Math.max(0,Math.floor((s-l)/6e4));return a<1?"less than a minute":a<60?`${a} min`:a<1440?`${Math.floor(a/60)} hour${a<120?"":"s"}`:`${Math.floor(a/1440)} day${a<2880?"":"s"}`}function Ke(l,s=Date.now()){if(l.issues?.includes("tracker_presence_conflict"))return[{kind:"unverified",text:"HA Person and selected tracker disagree"},{kind:"missing",text:"Map position withheld"}];if(!l.location)return[{kind:"missing",text:"No usable map position"}];let a=l.location.evidence,d=a?.card_source_label??a?.source_label,p=typeof d=="string"&&d.trim()?[{kind:"source",text:d}]:[],h=a?.reported_at?Date.parse(a.reported_at):NaN;if(Number.isFinite(h)&&h<=s+6e4)return[...p,...a.freshness==="stale"?[{kind:"stale",text:"Stale report"}]:[],{kind:"reported",text:`Location reported ${io(h,s)} ago`}];let f=a?.observed_at?Date.parse(a.observed_at):NaN;return Number.isFinite(f)&&f<=s+6e4?[...p,{kind:"observed",text:`${l.location.origin==="ha_person"?"HA Person":"HA tracker"} updated ${io(f,s)} ago`}]:[...p,{kind:"unknown",text:"Update time unavailable"}]}function Ye(l,s,a=42){let d=[];for(let p of l){let h=s(p.location),f=d.find(g=>Math.hypot(g.point.x-h.x,g.point.y-h.y)<a);f?f.members.push(p):d.push({point:h,members:[p]})}return d}function lo(l){let s=Math.max(0,Math.min(1,(l.x-24)/160,(l.y-24)/168));return{paddingTopLeft:[Math.floor(112*s),Math.floor(120*s)],paddingBottomRight:[Math.floor(48*s),Math.floor(48*s)]}}function Oi(l){if(!l||l.type!=="custom:homecircle-card")throw new Error("Use the HomeCircle card type.");if(l.map_tiles&&!["none","osm","satellite"].includes(l.map_tiles))throw new Error("Choose a supported map background.");if(l.hidden_members&&(!Array.isArray(l.hidden_members)||l.hidden_members.some(s=>typeof s!="string")))throw new Error("Hidden members must be a list.");if(l.fill_screen!==void 0&&typeof l.fill_screen!="boolean")throw new Error("Fill screen must be on or off.");return{...l,title:String(l.title||"HomeCircle"),map_tiles:l.map_tiles||"osm",fill_screen:l.fill_screen||!1,hidden_members:l.hidden_members||[]}}function Te(l){let s={full:"Full",medium:"Medium",low:"Low",very_low:"Very Low"}[l.battery_status?.value];return s?`${s} (last report)`:"Unknown"}var es={tracker_presence_conflict:"The HA Person and a selected GPS tracker disagree about Home or Away. Check which trackers are linked to the HA Person and when each last updated.",person_tracker_location_conflict:"The HA Person and its active GPS tracker have different positions. The map position is withheld until they agree.",active_source_unavailable:"The HA Person's active tracker is unavailable. Check the tracker integration and its last update.",active_source_locationless:"The active tracker has no usable GPS position. Presence may still be available.",ambiguous_gps_sources:"More than one selected GPS tracker could supply the position. Review tracker selection.",location_source_unverified:"The map position's source could not be verified against the selected trackers.",location_report_source_mismatch:"The configured report-time sensor belongs to a different source. Review this person's report-time settings.",residence_zone_unavailable:"A configured residence zone is unavailable. Check the zone in Home Assistant.",person_unavailable:"The HA Person is unavailable. Check the Person and its linked trackers in Home Assistant.",tracker_unavailable:"The selected tracker is unavailable. Check its integration in Home Assistant.",ambiguous_zone_name:"More than one HA zone has this name. Review the configured places.",unresolved_place:"This HA place could not be matched to a configured HomeCircle place.",legacy_home_membership:"HA reported Home without a zone ID. HomeCircle used the primary Home zone.",legacy_zone_name:"HA reported a place name without a zone ID. HomeCircle matched the unique configured zone.",gps_inside_zone_ha_pending:"A recent GPS report is well inside this configured place, but HA still says Away. HA may not have reassessed a newly added zone yet."};function O(l,s,a){let d=document.createElement(l);return s&&(d.className=s),a!=null&&(d.textContent=String(a)),d}function qt(l,s=!1){if(!l)return"Unknown";let a=new Date(l);return Number.isFinite(a.getTime())?new Intl.DateTimeFormat(void 0,{dateStyle:"medium",timeStyle:s?"medium":"short"}).format(a):"Unknown"}function Ii(l){if(!l||!Number.isFinite(l.latitude)||!Number.isFinite(l.longitude))return"Unknown";let s=`${l.latitude.toFixed(6)}, ${l.longitude.toFixed(6)}`;return l.accuracy==null?s:`${s} \xB7 accuracy ${l.accuracy} m`}function at(l,s,a){let d=O("div","detail-row");d.append(O("dt",null,s),O("dd",null,a)),l.append(d)}function ie(l,s){let a=O("section");return a.append(O("h3",null,s)),l.append(a),a}function Xe(l){return l?.replace(/^Tracker: /,"").replace(/ · Mobile App$/," \xB7 Home Assistant")}function ho(l,s,a){let d=l.querySelector(".older-activity")?.open||!1,p=l.querySelector(".technical-details")?.open||!1;l.replaceChildren();let h=s.location?.evidence,f=s.diagnostics||{},g=s.issues||[],P=ie(l,"Current status"),_=O("dl");if(at(_,"Status",jt[s.presence]||"Unknown"),at(_,"Place",s.place||"No named place"),at(_,"Map",s.focusable?s.map_visible===!1?"Hidden from Everyone; selectable on the map":"Shown on the map":"Position unavailable or withheld"),at(_,"Battery",s.battery==null?Te(s):`${s.battery}%${s.charging===!0?" \xB7 charging":""}`),s.battery==null&&s.battery_status&&at(_,"Battery reported",qt(s.battery_status.reported_at,!0)),at(_,"Driving",s.driving?.value===!0?s.driving.status==="current"?"Current report":"Last reported or unverified":s.driving?.value===!1?"Not reported as driving":"Unknown"),s.speed?.value!=null&&at(_,"Speed",`${s.speed.value} ${s.speed.unit||""}`),P.append(_),g.length){let y=ie(l,"Needs attention");y.className="detail-attention";let J=O("ul");for(let Q of g)J.append(O("li",null,es[Q]||Q));y.append(J)}let C=ie(l,"Location report"),j=Ke(s).filter(y=>y.kind!=="source").map(y=>y.text).join(" \xB7 ");C.append(O("p","report-summary",j));let Z=O("dl");at(Z,"Tracker used for map",Xe(h?.source_label)||"No usable map position"),s.location&&(at(Z,"Source location report",h?.reported_at?qt(h.reported_at):"Not provided by this tracker"),at(Z,s.location.origin==="ha_person"?"Home Assistant Person updated":"Home Assistant tracker updated",qt(h?.observed_at))),C.append(Z);let w=O("p","detail-note",s.location?"A Home Assistant update may not mean a new GPS fix. An older location report can still show the correct position while stationary.":"Open tracker diagnostics below to check the selected trackers and their last recorded positions.");C.append(w);let z=s.location_request;if(z?.enabled){let y=ie(l,"Location requests"),J=O("dl");at(J,"Automatic requests","Enabled for the selected Home Assistant phone tracker after 15 quiet minutes"),at(J,"Last request attempted",z.requested_at?qt(z.requested_at):"None yet"),at(J,"Request status",{tracker_responded:"A later tracker report arrived",waiting:"Waiting for a tracker report",no_response:"No later tracker report received",response_unverified:"Response to a request before HA restarted cannot be verified",send_failed:"Home Assistant could not send the request",quiet_pending:"Waiting for 15 quiet minutes",request_pending:"Request will be sent on the next check",unsupported:"No Home Assistant phone notification target is available",not_selected:"The Home Assistant phone tracker is not the current map source",no_position:"No current map position is available",unavailable:"Automatic requests are temporarily unavailable"}[z.status]||"Unknown"),z.next_request_at&&(at(J,"Request limit","50 requests used in the last 24 hours"),at(J,"Next request allowed",qt(z.next_request_at))),y.append(J),y.append(O("p","detail-note","A request does not guarantee delivery or a new GPS fix. Attempts are at least one minute apart, with up to 50 in a rolling 24 hours."))}let q=ie(l,"Recent activity");q.className="recent-activity",q.append(O("p","detail-note","Observed by HomeCircle; gaps and restarts do not confirm a journey. Up to 100 events per person, kept for seven days. Freshness changes are limited to 25 entries to preserve arrivals, departures and request results. No coordinates or routes are stored."));let D=s.activity?.events||[];s.activity?.persistent===!1&&q.append(O("p","detail-note","Activity storage is unavailable. Events are kept only while HomeCircle is running.")),D.length||q.append(O("p","detail-note","No activity recorded yet. History begins when this feature starts."));let A=y=>y.kind==="started"?"Observation started or resumed":y.kind==="presence"?`Status observed: ${jt[y.value]||"Unknown"}`:y.kind==="source"?`Map source observed: ${Xe(y.value)||"No usable map source"}`:y.kind==="freshness"?{fresh:"Location report observed: fresh",stale:"Location report observed: stale",unknown:"Location report freshness is unknown",unavailable:"Location report unavailable"}[y.value]||"Location report changed":y.kind==="automatic_refresh"?y.value==="requested"?"Automatic location update requested; delivery unconfirmed":"Automatic location update request could not be sent":y.kind==="refresh"?{requested:"Location update requested; delivery unconfirmed",checked:"Cloud reports checked",cooldown:"Refresh skipped: request cooldown",busy:"Refresh skipped: check already in progress",limited:"Refresh skipped: daily request limit",disabled:"Refresh skipped: phone requests disabled",not_allowed:"Refresh skipped: control permission required",unsupported:"Refresh unavailable for this tracker",no_position:"Refresh skipped: no usable position",fresh:"Refresh skipped: report already fresh",send_failed:"Location update request could not be sent",unavailable:"Location check unavailable"}[y.value]||"Location check completed":"Activity observed",X=y=>{let J=O("ol","activity-list");for(let Q of y){let Ut=O("li"),lt=O("time",null,qt(Q.observed_at,!0));lt.dateTime=Q.observed_at,Ut.append(lt,O("span",null,A(Q))),Q.reported_at&&Ut.append(O("small",null,`Tracker report: ${qt(Q.reported_at)}`)),J.append(Ut)}return J};if(D.length&&q.append(X(D.slice(0,5))),D.length>5){let y=O("details","older-activity");y.open=d,y.append(O("summary",null,`Show ${D.length-5} older events`),X(D.slice(5))),q.append(y)}let F=O("details","technical-details");F.open=p,F.append(O("summary",null,"Tracker diagnostics and coordinates"));let yt=O("div","technical-body");F.append(yt),l.append(F);let ct=ie(yt,"Map evidence"),b=O("dl");at(b,"Selection reason",f.source_selection_reason||"Following Home Assistant Person."),at(b,"Map coordinates",Ii(s.location)),at(b,"Time source",s.location?h?.reported_at?h.report_status==="explicit_sensor"?"Configured report-time sensor":"Tracker supplied a location report time":"Home Assistant state or attribute update; GPS report time unavailable":"No usable map position"),ct.append(b);let H=ie(yt,"Home Assistant sources"),T=O("dl");f.person_entity&&(at(T,"HA Person",f.person_entity),at(T,"Person state",f.person_state||"Unavailable"),at(T,"Person updated",qt(f.person_updated_at)),at(T,"HA Person coordinates",Ii(f.person_position))),at(T,"Active HA source",f.active_source==="other"?"Another HA tracker, outside this person's HomeCircle selection":Xe(f.selected_trackers?.find(y=>y.entity_id===f.active_source)?.label)||f.active_source||"Unknown"),H.append(T);let M=f.selected_trackers||[];if(M.length){H.append(O("h4",null,"Selected trackers"));for(let y of M){let J=O("div","tracker-detail");J.append(O("strong",null,Xe(y.label)||y.entity_id),O("span",null,y.entity_id),O("span",null,`State: ${y.state||"Unavailable"}${y.active?" \xB7 active HA source":""}`),O("span",null,`HA update: ${qt(y.updated_at)}`),O("span",null,`Coordinates: ${Ii(y.position)}`));let Q=O("button","history-button","View HA history");Q.type="button",Q.addEventListener("click",()=>{l.closest("dialog")?.close(),a.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:y.entity_id,view:"history"}}))}),J.append(Q),H.append(J)}H.append(O("p","detail-note","HA history shows recorded samples when Recorder has them. Gaps do not show the exact route traveled."))}else H.append(O("p","detail-note","No trackers selected."));g.length||C.append(O("p","detail-note","No HomeCircle conflicts detected."))}function Ni(l,s,a,d){let p=document.querySelector("home-assistant")?.shadowRoot||document.body;if(p.querySelector("dialog.homecircle-member-details"))return;let h=l._data?.members?.find(D=>D.id===a);if(!h)return;let f=O("dialog","homecircle-member-details");f.setAttribute("aria-label",`${h.name} details`);let g=O("style");g.textContent=`
    dialog.homecircle-member-details { width: min(620px, calc(100vw - 24px)); max-height: min(88dvh, 850px); padding: 0; border: 0; border-radius: 20px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #222); box-shadow: 0 20px 70px #0008; }
    dialog.homecircle-member-details::backdrop { background: #000a; }
    dialog.homecircle-member-details[open] { display: flex; flex-direction: column; overflow: hidden; font: 14px/1.5 system-ui, sans-serif; }
    .homecircle-member-details * { box-sizing: border-box; }
    .homecircle-member-details header { display: flex; align-items: center; gap: 12px; padding: 18px 22px; border-bottom: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details .details-avatar { width: 64px; height: 64px; flex: 0 0 64px; border-radius: 50%; background: var(--secondary-background-color, #eee); display: grid; place-items: center; position: relative; overflow: hidden; font-weight: 600; font-size: 20px; }
    .homecircle-member-details .details-avatar img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
    .homecircle-member-details h2 { flex: 1; margin: 0; font: 650 21px/1.3 system-ui, sans-serif; }
    .homecircle-member-details h3 { margin: 0 0 10px; font: 650 16px/1.3 system-ui, sans-serif; }
    .homecircle-member-details h4 { margin: 14px 0 6px; font: 600 14px/1.3 system-ui, sans-serif; }
    .homecircle-member-details header, .homecircle-member-details footer { flex-shrink: 0; }
    .homecircle-member-details .body { padding: 16px 22px; overflow-y: auto; min-height: 0; }
    .homecircle-member-details section + section { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details dl { margin: 0; }
    .homecircle-member-details .report-summary { margin: 0 0 10px; font-weight: 600; }
    .homecircle-member-details .detail-attention { border-left: 3px solid var(--warning-color, #c77700); padding-left: 12px; }
    .homecircle-member-details .technical-details { margin-top: 20px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details summary { padding: 12px 0; min-height: 44px; cursor: pointer; font-weight: 600; }
    .homecircle-member-details summary:focus-visible { outline: 3px solid var(--primary-color, #03a9f4); }
    .homecircle-member-details .technical-body { padding-top: 6px; }
    .homecircle-member-details .detail-row { display: grid; grid-template-columns: minmax(130px, 40%) minmax(0, 1fr); gap: 8px; padding: 5px 0; }
    .homecircle-member-details dt { color: var(--secondary-text-color, #666); }
    .homecircle-member-details dd { margin: 0; overflow-wrap: anywhere; }
    .homecircle-member-details .tracker-detail { display: grid; gap: 3px; margin: 10px 0; padding: 10px; border-radius: 9px; background: var(--secondary-background-color, #eee); overflow-wrap: anywhere; }
    .homecircle-member-details .tracker-detail span, .homecircle-member-details .detail-note { color: var(--secondary-text-color, #666); font-size: 13px; }
    .homecircle-member-details .activity-list { list-style: none; padding: 0; margin: 0; }
    .homecircle-member-details .activity-list li { display: grid; gap: 3px; padding: 9px 0; border-bottom: 1px solid var(--divider-color, #ddd); overflow-wrap: anywhere; }
    .homecircle-member-details .activity-list time, .homecircle-member-details .activity-list small { color: var(--secondary-text-color, #666); font-size: 12px; }
    .homecircle-member-details .history-button { color: var(--primary-color, #03a9f4); }
    .homecircle-member-details ul { margin: 0; padding-left: 20px; }
    .homecircle-member-details li + li { margin-top: 8px; }
    .homecircle-member-details footer { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; padding: 12px 22px 18px; border-top: 1px solid var(--divider-color, #ddd); }
    .homecircle-member-details .refresh-feedback { flex: 1 1 100%; min-height: 18px; margin: 0; color: var(--secondary-text-color, #666); font-size: 13px; }
    .homecircle-member-details button { min-height: 44px; padding: 8px 12px; border: 1px solid var(--divider-color, #ccc); border-radius: 9px; background: var(--card-background-color, #fff); color: inherit; font: inherit; cursor: pointer; }
    .homecircle-member-details button:focus-visible { outline: 3px solid var(--primary-color, #03a9f4); }
    @media (max-width: 420px) {
      .homecircle-member-details header, .homecircle-member-details .body, .homecircle-member-details footer { padding-left: 14px; padding-right: 14px; }
      .homecircle-member-details .detail-row { grid-template-columns: minmax(96px, 36%) minmax(0, 1fr); padding: 6px 0; }
      .homecircle-member-details footer button { flex: 1 1 auto; }
    }
  `;let P=O("header"),_=O("h2",null,h.name);_.tabIndex=-1;let C=te(h,"details-avatar");P.append(C,_);let j=O("button",null,"Close");j.type="button",j.addEventListener("click",()=>f.close());let Z=O("div","body");ho(Z,h,l);let w=O("footer"),z=O("p","refresh-feedback");z.setAttribute("role","status"),z.setAttribute("aria-live","polite"),z.textContent="Refresh checks Home Assistant's saved data.";let q=O("button",null,"Refresh details");if(q.type="button",q.addEventListener("click",async()=>{if(l._hass?.connected===!1||s.connected===!1){z.textContent="Home Assistant is disconnected. Try again when it reconnects.";return}if(l._busy){z.textContent="An update is already in progress. Try again shortly.";return}q.disabled=!0,q.textContent="Checking\u2026",z.textContent="Checking Home Assistant for updated details\u2026";let D=l._data?.members?.find(A=>A.id===a);try{if(await l._load(),!f.isConnected)return;let A=l._data?.members?.find(H=>H.id===a);if(!A){z.textContent="Could not refresh details. Try again.";return}let X=te(A,"details-avatar");C.replaceWith(X),C=X,_.textContent=A.name,f.setAttribute("aria-label",`${A.name} details`),ho(Z,A,l);let F=D?.location?.evidence?.reported_at||D?.location?.evidence?.observed_at,yt=A.location?.evidence?.reported_at||A.location?.evidence?.observed_at,ct=new Intl.DateTimeFormat(void 0,{hour:"numeric",minute:"2-digit"}).format(new Date),b=D?.location?.evidence?.source_label!==A.location?.evidence?.source_label||D?.location?.origin!==A.location?.origin;z.textContent=b?`Map source changed. Checked at ${ct}.`:yt&&yt!==F?`Report time changed. Checked at ${ct}.`:yt?`Checked at ${ct}. No newer tracker time.`:`Checked at ${ct}. No tracker time available.`}catch{f.isConnected&&(z.textContent="Could not refresh details. Try again.")}finally{q.disabled=!1,q.textContent="Refresh details"}}),w.append(z,q),s.user?.is_admin===!0){let D=O("button",null,"Manage member settings");D.type="button",D.addEventListener("click",()=>{f.close(),je(l,l._hass||s,a,A=>Ni(l,l._hass||s,A,d))}),w.append(D)}return w.append(j),f.append(g,P,Z,w),p.append(f),l._memberDialog=f,f.addEventListener("close",()=>{f.remove(),l._memberDialog===f&&(l._memberDialog=null),d?.isConnected&&d.focus({preventScroll:!0})}),f.showModal(),_.focus({preventScroll:!0}),Z.scrollTop=0,f}var Ri=Kn(zi(),1);var co=l=>`https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/${l}/{z}/{x}/{y}.png`,uo=l=>new Date(l).toISOString().replace(/[-:T]/g,"").slice(0,12);function po(l){let s=Date.parse(l?.meta?.valid);if(!Number.isFinite(s))throw new Error("Radar time unavailable");return[30,25,20,15,10,5,0].map(a=>({minutes:a,time:s-a*6e4,kind:"Observed",url:co(`ridge::USCOMP-N0Q-${uo(s-a*6e4)}`)}))}function Zi(l,s=Date.now()){let a=Date.parse(l?.model_init_utc);if(!Number.isFinite(a)||a>s||s-a>1080*6e4)throw new Error("Forecast time unavailable");let d=Math.floor((s-a)/(15*6e4))*15+15,p=[];for(let h=d;h<=Math.min(d+120,1080);h+=15)p.push({minutes:h,time:a+h*6e4,kind:"Forecast",init:a,url:co(`hrrr::REFD-F${String(h).padStart(4,"0")}-${uo(a)}`)});if(!p.length)throw new Error("Forecast expired");return p}function Je(l){return l?.time?`${l.kind} \xB7 ${new Date(l.time).toLocaleString(void 0,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"})}`:"Observed \xB7 time unavailable"}var fo="https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png",Qe=class{constructor(s,a,d){this.card=s,this.enabled=!1,this.opacity=.4,this.showControls=!1;try{this.showControls=window.localStorage.getItem(this.preferenceKey())==="true"}catch{}this.controls=document.createElement("div"),this.controls.className="radar-controls",this.toggle=document.createElement("button"),this.toggle.type="button",this.toggle.textContent="Radar",this.toggle.title="U.S. weather radar from Iowa Environmental Mesonet. Enabling sends viewed map areas to IEM.",this.toggle.onclick=()=>{s._config.map_tiles!=="none"&&(this.enabled=!this.enabled,this.sync())},this.options=document.createElement("div"),this.options.className="radar-options";let p=document.createElement("label");p.textContent="Opacity ",this.range=document.createElement("input"),this.range.type="range",this.range.min="10",this.range.max="100",this.range.value=String(this.opacity*100),this.range.setAttribute("aria-label","Radar opacity"),this.value=document.createElement("output"),this.value.textContent=`${this.range.value}%`,this.range.oninput=()=>{this.opacity=Number(this.range.value)/100,this.value.textContent=`${this.range.value}%`,this.layer?.setOpacity(this.currentFrame?0:this.opacity);for(let f of this.frames||[])f.layer.setOpacity(f===this.currentFrame?this.opacity:0)},p.append(this.range,this.value);let h=document.createElement("div");h.className="radar-legend",h.textContent="Weak echoes \u2192 Strong echoes",this.options.append(p,h),this.controls.append(this.options),s._mapControls.insertBefore(this.toggle,s._satelliteButton),this.note=document.createElement("div"),this.note.className="radar-note",this.note.setAttribute("role","status"),this.playback=document.createElement("div"),this.playback.className="radar-playback",this.play=document.createElement("button"),this.play.type="button",this.play.onclick=()=>this.playing?this.stopPlayback():this.startPlayback(),this.frameLabel=document.createElement("span"),this.timeline=document.createElement("select"),this.timeline.setAttribute("aria-label","Radar time range");for(let[f,g]of[["past","Past 30 min"],["future","Future 2 hr"]]){let P=document.createElement("option");P.value=f,P.textContent=g,this.timeline.append(P)}this.timeline.onchange=async()=>{this.stopPlayback(),this.timeline.value==="future"&&(this.forecast||await this.loadMetadata(),this.enabled&&this.timeline.value==="future"&&this.startPlayback())},this.playback.append(this.play,this.timeline,this.frameLabel),d.append(this.playback,this.note),this.resetPlaybackControls(),a.append(this.controls),this.sync()}sync(){let s=this.card._map,a=this.card._config.map_tiles==="none";if(a&&(this.enabled=!1),this.controls.hidden=a,this.toggle.setAttribute("aria-pressed",String(this.enabled)),this.options.hidden=!this.enabled||!this.showControls,this.note.hidden=this.playback.hidden=!this.enabled,!this.enabled||!s){this.removeLayer();return}if(this.layer)return;if(!s.getPane("homecircle-radar")){let p=s.createPane("homecircle-radar");p.style.zIndex="350",p.style.pointerEvents="none"}this.observed=this.forecast=this.forecastMetadata=null,this.metadataAt=null,this.resetPlaybackControls();let d=Ri.tileLayer(fo,{pane:"homecircle-radar",maxNativeZoom:12,maxZoom:19,opacity:this.opacity,attribution:'Radar: <a href="https://mesonet.agron.iastate.edu/" target="_blank" rel="noopener">Iowa Environmental Mesonet / NEXRAD</a>',referrerPolicy:"no-referrer"});this.layer=d,this.failed=!1,this.note.textContent="Loading U.S. radar\u2026",d.on("loading",()=>{this.layer===d&&(this.failed=!1)}),d.on("tileerror",()=>{this.layer===d&&(this.failed=!0,this.note.textContent="Some radar tiles unavailable. Map and people still work.")}),d.on("load",()=>{this.layer!==d||this.failed||this.playing||(this.showObservedStatus(),this.note.title="Radar can be delayed. Transparent areas may mean no echoes or missing coverage. Observed times describe the mosaic, not each individual radar scan. Forecast times describe HRRR predictions.")}),d.addTo(s),this.loadMetadata(),this.onResume=()=>{!document.hidden&&this.enabled&&this.card.isConnected&&(this.stopPlayback(),this.loadMetadata(),d.redraw())},document.addEventListener("visibilitychange",this.onResume),this.timer=setInterval(()=>{this.card.isConnected&&!document.hidden&&(this.stopPlayback(),d.redraw(),this.loadMetadata())},3e5)}resetPlaybackControls(){this.play.textContent="\u25B6",this.play.setAttribute("aria-label","Animate radar"),this.play.title="Play the selected observed or forecast radar frames",this.play.setAttribute("aria-pressed","false"),this.frameLabel.textContent=Je(this.observed?.at(-1))}showObservedStatus(){this.note.textContent=this.observed?"Observed U.S. radar \xB7 updates about every 5 min \xB7 imagery can be delayed":"Observed U.S. radar \xB7 time unavailable \xB7 imagery may be delayed"}useUntimedRadar(){this.observed=null,!this.playing&&this.layer&&(this.layer.setUrl(fo),this.resetPlaybackControls(),this.showObservedStatus())}async loadMetadata(){this.metadataAbort?.abort();let s=new AbortController;this.metadataAbort=s;let a=setTimeout(()=>{s.abort(),this.metadataAbort===s&&this.enabled&&this.layer&&(this.forecast=this.forecastMetadata=null,this.metadataAt=null,this.useUntimedRadar())},1e4),d={signal:s.signal,referrerPolicy:"no-referrer",credentials:"omit"},p=async h=>{let f=await window.fetch(h,d);if(!f.ok)throw new Error("Weather metadata unavailable");return f.json()};try{let h=await Promise.allSettled([p("https://mesonet.agron.iastate.edu/data/gis/images/4326/USCOMP/n0q_0.json"),p("https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_1080.json")]);if(s.signal.aborted||this.metadataAbort!==s||!this.enabled||!this.layer)return;if(h[0].status==="fulfilled")try{this.observed=po(h[0].value)}catch{this.observed=null}else this.observed=null;if(h[1].status==="fulfilled")try{this.forecast=Zi(h[1].value),this.forecastMetadata=h[1].value}catch{this.forecast=this.forecastMetadata=null}else this.forecast=this.forecastMetadata=null;this.metadataAt=Date.now(),!this.playing&&this.observed?(this.layer.setUrl(this.observed.at(-1).url),this.resetPlaybackControls(),this.showObservedStatus()):this.observed||this.useUntimedRadar()}finally{clearTimeout(a),this.metadataAbort===s&&(this.metadataAbort=null)}}async startPlayback(){if(!this.enabled||!this.layer||this.playing||document.hidden)return;if(this.metadataAt&&Date.now()-this.metadataAt>=3e5){let a=this.playToken=(this.playToken||0)+1,d=this.layer,p=this.timeline.value;if(await this.loadMetadata(),a!==this.playToken||this.layer!==d||!this.enabled||document.hidden||this.timeline.value!==p)return}if(this.timeline.value==="future"&&this.forecastMetadata)try{this.forecast=Zi(this.forecastMetadata)}catch{this.forecast=null}let s=this.timeline.value==="future"?this.forecast:this.observed;if(!s?.length){this.note.textContent=this.timeline.value==="future"?"Forecast unavailable. Showing latest observed radar.":"Radar times unavailable. Try again shortly.";return}this.playing=!0,this.frames=[],this.currentFrame=null,this.waitingSince=Date.now(),this.play.textContent="\u2161",this.play.setAttribute("aria-label","Pause radar animation"),this.play.title="Pause and return to latest radar",this.play.setAttribute("aria-pressed","true"),this.frameLabel.textContent="Loading animation\u2026";for(let a of s){let d=Ri.tileLayer(a.url,{...this.layer.options,opacity:0}),p={...a,layer:d,ready:!1,failed:!1};this.frames.push(p),d.on("loading",()=>{p.ready=p.failed=!1}),d.on("tileerror",()=>{p.failed=!0}),d.on("load",()=>{p.ready=!p.failed}),d.addTo(this.card._map)}this.onMapMove=()=>this.stopPlayback(),this.onVisibility=()=>{document.hidden&&this.stopPlayback()},this.card._map.on("movestart",this.onMapMove),document.addEventListener("visibilitychange",this.onVisibility),this.animationTimer=setInterval(()=>this.advanceFrame(),900)}advanceFrame(){if(!this.playing)return;if(!this.card.isConnected||document.hidden){this.stopPlayback();return}if(this.frames.some(d=>d.failed)){this.stopPlayback(),this.note.textContent="Animation unavailable. Showing latest available radar.";return}let s=this.currentFrame?this.frames.indexOf(this.currentFrame):-1,a=this.frames[(s+1)%this.frames.length];if(!a.ready){Date.now()-this.waitingSince>2e4&&(this.stopPlayback(),this.note.textContent="Animation timed out. Showing latest observed radar.");return}this.waitingSince=Date.now(),this.layer.setOpacity(0),this.currentFrame?.layer.setOpacity(0),a.layer.setOpacity(this.opacity),this.currentFrame=a,this.frameLabel.textContent=Je(a),this.note.textContent=a.kind==="Forecast"?`HRRR prediction \xB7 model run ${Je({kind:"",time:a.init}).replace(/^ · /,"")} \xB7 not observed radar`:"Observed radar \xB7 5-minute steps \xB7 radar can be delayed"}stopPlayback(){this.playToken=(this.playToken||0)+1,clearInterval(this.animationTimer),this.animationTimer=null,this.onMapMove&&this.card._map?.off("movestart",this.onMapMove),document.removeEventListener("visibilitychange",this.onVisibility),this.onMapMove=this.onVisibility=null;for(let a of this.frames||[])a.layer.remove(),a.layer.off();this.frames=[],this.currentFrame=null;let s=this.playing;this.playing=!1,this.layer?.setOpacity(this.opacity),this.resetPlaybackControls(),s&&!this.failed&&this.showObservedStatus()}preferenceKey(){return`${this.card._mapPreferenceKey()}:radar-controls`}setShowControls(s){this.showControls=!!s;try{window.localStorage.setItem(this.preferenceKey(),String(this.showControls))}catch{}this.sync()}removeLayer(){this.metadataAbort?.abort(),this.metadataAbort=null,document.removeEventListener("visibilitychange",this.onResume),this.onResume=null,this.stopPlayback(),this.observed=this.forecast=this.forecastMetadata=null,this.metadataAt=null,this.resetPlaybackControls(),clearInterval(this.timer),this.timer=null,this.layer&&(this.layer.remove(),this.layer.off(),this.layer=null)}dispose(){this.enabled=!1,this.removeLayer(),this.toggle.setAttribute("aria-pressed","false"),this.options.hidden=this.note.hidden=this.playback.hidden=!0}};var mo="HomeCircle",is=l=>l==="HomeCircle"||/^HomeCircle - Beta \d+$/.test(l)?mo:l;function x(l,s,a){let d=document.createElement(l);return s&&(d.className=s),a!==void 0&&(d.textContent=a),d}function Pt(l,s,a){let d=x("button",a,l);return d.type="button",d.addEventListener("click",s),d}var Hi=class extends HTMLElement{constructor(){super(),this.attachShadow({mode:"open"}),this._mode="overview",this._generation=0,this._refreshToken=0,this._integrationVersion=Jn.version}static getConfigElement(){return document.createElement("homecircle-card-editor")}static getStubConfig(){return{type:"custom:homecircle-card",title:mo,map_tiles:"osm"}}getCardSize(){return 8}getGridOptions(){return{columns:12,min_columns:6,rows:"auto"}}setConfig(s){let a=this._config;if(this._config=Oi(s),this.toggleAttribute("fill-screen",this._config.fill_screen),this._config.fill_screen||this._setKiosk(!1),a?.map_tiles!==this._config.map_tiles||a?.title!==this._config.title){if(this._mapBackground=this._config.map_tiles,this._config.map_tiles!=="none")try{let d=window.localStorage.getItem(this._mapPreferenceKey());["osm","satellite"].includes(d)&&(this._mapBackground=d)}catch{}this._destroyMap()}if(!a||a.title!==this._config.title){this._mapHeight=null;try{let d=Number(window.localStorage.getItem(this._heightPreferenceKey()));Number.isFinite(d)&&d>=220&&(this._mapHeight=d)}catch{}}this._applyMapHeight(),this._syncMapControls(),this._cancelSelectionRefresh(),this._mode="overview",this._fit=!0,this.isConnected&&(this._layout(),this._fitScreen(),this._render(),this._load())}set hass(s){let a=this._hass?.connection!==s.connection,d=this._hass?.connected===!1&&s.connected!==!1,p=this._hass?.user?.id&&this._hass.user.id===s.user?.id;if(this._hass=s,this._syncSettingsVisibility(),a&&(clearTimeout(this._timeout),this._generation++,this._busy=!1,p&&this._data?this._temporaryFailure("Reconnecting to Home Assistant\u2026 Showing last received locations."):this._clear("Connecting to Home Assistant\u2026")),s.connected===!1){clearTimeout(this._timeout),this._generation++,this._busy=!1,this._temporaryFailure("Home Assistant is disconnected. Showing last received locations.");return}this.isConnected&&(a||d)&&this._load()}connectedCallback(){this._layout(),this._config?.fill_screen&&new URLSearchParams(window.location.search).get("homecircle_kiosk")==="1"&&this._setKiosk(!0),this._onWindowResize||=()=>this._fitScreen(),window.addEventListener("resize",this._onWindowResize),this._fitScreen(),this._render(),this._load(),clearInterval(this._timer),this._timer=setInterval(()=>this._load(),15e3)}disconnectedCallback(){this._finishMapResize(!1),this._cancelSelectionRefresh(),this._memberDialog?.close(),this._setKiosk(!1),window.removeEventListener("resize",this._onWindowResize),clearInterval(this._timer),clearTimeout(this._retry),clearTimeout(this._timeout),this._generation++,this._busy=!1,this._data=null,this._signature=null,this._mode="overview",this._destroyMap(),this.shadowRoot.replaceChildren(),this._shell=null}_fitScreen(){if(this._applyMapHeight(),!this._config?.fill_screen||!this.isConnected)return;let s=Math.max(480,Math.round(window.innerHeight-(this._kioskEnabled?0:this.getBoundingClientRect().top+8)));this.style.setProperty("--homecircle-screen-height",`${s}px`),this._map?.invalidateSize({pan:!1})}_setKiosk(s){!!this._kioskEnabled!==s&&(this._kioskEnabled=s,this.toggleAttribute("kiosk",s),this._syncKioskChrome(s),window.dispatchEvent(new CustomEvent("hass-kiosk-mode",{detail:{enable:s}})),this._syncKioskButton(),requestAnimationFrame(()=>requestAnimationFrame(()=>this._fitScreen())))}_syncKioskButton(){if(!this._kioskButton)return;let s=!!this._kioskEnabled,a=s?"Exit kiosk view":"Enter kiosk view";this._kioskButton.setAttribute("aria-label",a),this._kioskButton.title=a,this._kioskButton.setAttribute("aria-pressed",String(s)),this._kioskIcon.setAttribute("icon",s?"mdi:fullscreen-exit":"mdi:fullscreen")}_syncKioskChrome(s){if(this._kioskChromeStyle?.remove(),this._kioskChromeStyle=null,!s)return;let a=document.querySelector("home-assistant")?.shadowRoot?.querySelector("home-assistant-main")?.shadowRoot?.querySelector("ha-panel-lovelace")?.shadowRoot?.querySelector("hui-root")?.shadowRoot;if(!a)return;let d=document.createElement("style");d.textContent=".header { display: none !important; } hui-view-container { padding-top: 0 !important; }",a.append(d),this._kioskChromeStyle=d}_toggleKiosk(){let s=!this._kioskEnabled,a=new URL(window.location.href);s?a.searchParams.set("homecircle_kiosk","1"):a.searchParams.delete("homecircle_kiosk"),window.history.replaceState(window.history.state,"",a),this._setKiosk(s)}_syncSettingsVisibility(){this._settingsButton&&(this._settingsButton.hidden=this._hass?.user?.is_admin!==!0)}_openSettings(){this._hass?.user?.is_admin===!0&&je(this,this._hass)}_layout(){if(this._shell||!this._config)return;let s=x("style");s.textContent=Xn+Ai,this._shell=x("ha-card");let a=x("header"),d=x("div");d.append(x("div","eyebrow","HOME \xB7 TOGETHER")),this._title=x("h2"),d.append(this._title),this._overview=Pt("Everyone \u2197",()=>this._choose("overview"),"overview");let p=x("div","header-actions");this._kioskButton=Pt("",()=>this._toggleKiosk(),"kiosk-toggle"),this._kioskIcon=x("ha-icon"),this._kioskIcon.setAttribute("aria-hidden","true"),this._kioskButton.append(this._kioskIcon),this._syncKioskButton(),this._settingsButton=Pt("",()=>this._openSettings(),"settings-toggle");let h=x("ha-icon");h.setAttribute("icon","mdi:cog"),h.setAttribute("aria-hidden","true"),this._settingsButton.append(h),this._settingsButton.setAttribute("aria-label","HomeCircle settings"),this._settingsButton.title="HomeCircle settings",this._syncSettingsVisibility(),p.append(this._kioskButton,this._settingsButton,this._overview),a.append(d,p),this._status=x("div","status"),this._status.setAttribute("role","status"),this._status.setAttribute("aria-live","polite"),this._locationFeedback=x("div","location-feedback"),this._locationFeedback.setAttribute("role","status"),this._locationFeedback.setAttribute("aria-live","polite"),this._providerAlerts=x("div","provider-alerts");let f=x("div","map-wrap");this._mapNode=x("div","map"),this._mapNode.setAttribute("aria-label","Household locations"),this._mapNote=x("div","map-note");let g=x("div","map-footer");this._mapControls=x("div","map-controls"),this._mapControls.setAttribute("role","group"),this._mapControls.setAttribute("aria-label","Map view"),this._streetButton=Pt("Street",()=>this._setMapBackground("osm")),this._satelliteButton=Pt("Satellite",()=>this._setMapBackground("satellite")),this._satelliteButton.title="USGS imagery \xB7 detailed coverage in the U.S.",this._mapControls.append(this._streetButton,this._satelliteButton),this._syncMapControls(),g.append(this._mapNote),this._mapWrap=f,this._resizeHandle=x("div","map-resize"),this._resizeHandle.tabIndex=0,this._resizeHandle.setAttribute("role","separator"),this._resizeHandle.setAttribute("aria-orientation","horizontal"),this._resizeHandle.setAttribute("aria-label","Resize map height"),this._resizeHandle.title="Drag to resize map. Arrow keys adjust height; Home resets.",this._resizeHandle.addEventListener("pointerdown",_=>{_.button!==0||this._mapDrag||(_.preventDefault(),this._resizeHandle.focus({preventScroll:!0}),this._mapDrag={id:_.pointerId,y:_.clientY,height:this._mapNode.getBoundingClientRect().height,previous:this._mapHeight},this._resizeHandle.setPointerCapture?.(_.pointerId))}),this._resizeHandle.addEventListener("pointermove",_=>{this._mapDrag?.id===_.pointerId&&(this._mapHeight=this._mapDrag.height+_.clientY-this._mapDrag.y,this._applyMapHeight())}),this._resizeHandle.addEventListener("pointerup",_=>{this._mapDrag?.id===_.pointerId&&this._finishMapResize(!0)}),this._resizeHandle.addEventListener("pointercancel",()=>this._finishMapResize(!1)),this._resizeHandle.addEventListener("lostpointercapture",()=>this._finishMapResize(!0)),this._resizeHandle.addEventListener("keydown",_=>{["ArrowUp","ArrowDown","Home"].includes(_.key)&&(_.preventDefault(),this._mapHeight=_.key==="Home"?null:(this._mapHeight??this._mapNode.getBoundingClientRect().height)+(_.key==="ArrowDown"?20:-20),this._applyMapHeight(),this._saveMapHeight())}),f.append(this._mapNode,this._mapControls,g,this._resizeHandle),this._radarController=new Qe(this,f,g),this._applyMapHeight(),this._expanded=x("div","expanded"),this._categories=x("div","categories"),this._members=x("div","members"),this._cityCredit=x("div","city-credit");let P=x("a",null,"City lookup: Photon \xB7 \xA9 OpenStreetMap contributors");P.href="https://www.openstreetmap.org/copyright",P.target="_blank",P.rel="noopener noreferrer",this._cityCredit.append(P),this._familyBar=x("div","family-refresh"),this._familyButton=Pt("Refresh family locations",()=>this._refreshFamily(),"family-refresh-button"),this._familyButton.title="Refreshes explicitly assigned supported trackers. Phone requests need member opt-in; unsupported trackers are skipped. One-minute cooldown and rolling daily limits apply.",this._familyFeedback=x("div","family-refresh-feedback"),this._familyFeedback.setAttribute("role","status"),this._familyFeedback.setAttribute("aria-live","polite"),this._familyBar.append(this._familyButton,this._familyFeedback),this._shell.append(a,this._status,this._locationFeedback,this._familyBar,this._providerAlerts,f,this._expanded,this._categories,this._members,this._cityCredit),this.shadowRoot.append(s,this._shell)}async _load(){if(!this._hass||!this._config||!this.isConnected||this._busy||this._hass.connected===!1)return;this._busy=!0;let s=++this._generation;this._timeout=setTimeout(()=>{s===this._generation&&(this._generation++,this._busy=!1,this._temporaryFailure("Connection timed out. Showing last received locations; retrying\u2026"))},1e4);try{let a=await this._hass.callWS({type:"homecircle/snapshot"});if(s!==this._generation||!this.isConnected)return;if(a.schema_version!==1)throw new Error("Unsupported household data version.");let d=!this._data,p=JSON.stringify(a)+Math.floor(Date.now()/6e4);this._data=a;let h=!!this._error;this._error=null,clearTimeout(this._retry),d&&(this._fit=!0),(d||h||p!==this._signature)&&this._render(),this._signature=p}catch(a){s===this._generation&&(a.code==="unauthorized"||a.message==="Unsupported household data version."?this._clear(a.code==="unauthorized"?"This HA user cannot view all selected household sources.":a.message):this._temporaryFailure(a.code==="not_ready"?"HomeCircle is starting\u2026 Showing last received locations; retrying\u2026":"Connection interrupted. Showing last received locations; retrying\u2026"))}finally{s===this._generation&&(clearTimeout(this._timeout),this._busy=!1)}}_temporaryFailure(s){this._error=s,this._render(),clearTimeout(this._retry),this.isConnected&&this._hass?.connected!==!1&&(this._retry=setTimeout(()=>this._load(),2e3))}_clear(s){clearTimeout(this._retry),this._cancelSelectionRefresh(),this._memberDialog?.close(),this._data=null,this._signature=null,this._mode="overview",this._error=s,this._destroyMap(),this._render()}_choose(s){this._mode===s&&this._selectionRefresh?.status==="checking"||(this._cancelSelectionRefresh(),this._expandedIds=null,this._mode=s,this._expanded?.replaceChildren(),this._fit=!0,this._render(),this._refreshSelectedLocation(s))}_cancelSelectionRefresh(){this._refreshToken++,clearTimeout(this._selectionTimeout),this._selectionRefresh=null,this._locationFeedback&&(this._locationFeedback.textContent="")}async _refreshSelectedLocation(s){let a=this._data?.members.find(f=>f.id===s);if(!a||a.location?.evidence?.freshness!=="stale"||!this.isConnected||this._hass?.connected===!1)return;let d=++this._refreshToken,p=a.location.evidence;this._selectionRefresh={id:s,status:"checking",reportedAt:p.reported_at,source:p.source_label,started:Date.now()},this._updateLocationFeedback();let h;try{let f=await Promise.race([this._hass.callWS({type:"homecircle/refresh_location",member_id:s}),new Promise((g,P)=>{h=this._selectionTimeout=setTimeout(()=>P(new Error("Check timed out")),15e3)})]);if(clearTimeout(h),d!==this._refreshToken||this._mode!==s||!this.isConnected)return;this._selectionRefresh.status=f.status,await this._load()}catch{if(clearTimeout(h),d!==this._refreshToken||this._mode!==s||!this.isConnected)return;this._selectionRefresh.status="unavailable"}this._updateLocationFeedback()}_updateLocationFeedback(){if(!this._locationFeedback)return;let s=this._selectionRefresh,a=s&&this._data?.members.find(h=>h.id===s.id);if(!s||this._mode!==s.id||!a){this._locationFeedback.textContent="";return}let d=a.location?.evidence;if(d?.source_label===s.source&&s.reportedAt&&Date.parse(d?.reported_at)>Date.parse(s.reportedAt)){this._locationFeedback.textContent=d.freshness==="stale"?"Newer report received; it is still stale.":"Newer location report received.";return}this._locationFeedback.textContent={checking:"Checking for a newer location report\u2026",requested:Date.now()-s.started<6e4?"Location update requested. Waiting for a newer report\u2026":"No newer location report received yet.",checked:"Checked cloud reports. No newer location report available.",cooldown:"A recent location check is on cooldown. No new request sent.",busy:"A location check is already in progress.",limited:"Location request limit reached. No new request sent.",disabled:"Phone location requests are off for this member.",not_allowed:"This HA user cannot request a location update.",unsupported:"This tracker does not support requesting a location update.",no_position:"No usable selected tracker position to refresh.",fresh:"The selected tracker report is already fresh.",send_failed:"Home Assistant could not send the location request.",unavailable:"Location refresh is temporarily unavailable."}[s.status]||"Location refresh is temporarily unavailable."}_openMemberDetails(s,a){Ni(this,this._hass,s,a)}_chooseFromMap(s,a){this._choose(s),[...this._members.querySelectorAll("[data-focus]")].find(d=>d.dataset.focus===s)?.focus(a?.detail?{preventScroll:!0}:void 0)}async _refreshFamily(){if(this._familyBusy||!this._data?.family_refresh?.available||this._hass?.connected===!1)return;let s=this._hass.connection;this._familyBusy=!0,this._familyMessageUntil=null,this._familyMessage="Sending family refresh request\u2026",this._updateFamilyFeedback();try{let a=await this._hass.callWS({type:"homecircle/refresh_family"});if(!this.isConnected||s!==this._hass.connection)return;this._familyMessage={requested:"Request accepted. Watching for newer reports\u2026",cooldown:"Family refresh is resting between requests.",limited:"The family refresh limit has been reached.",not_allowed:"You do not have permission to refresh every family member.",unsupported:"Family refresh is unavailable for the current tracker selection.",send_failed:"The family request failed. No refresh is confirmed.",unavailable:"Family refresh is temporarily unavailable."}[a.status]||"Family refresh is temporarily unavailable.",this._familyRetryAt=a.retry_at||null,a.retry_at&&(this._familyMessage+=` Next available ${this._familyRetryLabel(a.retry_at)}.`),a.status==="requested"&&(this._familyMessage=""),this._signature=null,this._load()}catch{this.isConnected&&s===this._hass.connection&&(this._familyMessage="Family refresh is temporarily unavailable.")}finally{this._familyMessageUntil=Date.now()+5*6e4,this._familyBusy=!1,this._updateFamilyFeedback()}}_familyRetryLabel(s){return new Date(s).toLocaleString(void 0,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"})}_updateFamilyFeedback(){if(!this._familyBar)return;(this._familyMessageUntil&&Date.now()>=this._familyMessageUntil||this._familyRetryAt&&Date.now()>=Date.parse(this._familyRetryAt))&&(this._familyMessage="",this._familyRetryAt=null);let s=this._data?.family_refresh;this._familyBar.hidden=!s?.available,this._familyButton.disabled=!!(this._familyBusy||s?.next_available_at||s?.status==="checking"||s?.status==="requested");let a=[];s?.next_available_at&&!this._familyBusy&&a.push(`Next family refresh: ${this._familyRetryLabel(s.next_available_at)}.`),this._familyMessage?a.push(this._familyMessage):s?.status==="checking"?a.push("Sending family refresh request\u2026"):s?.status==="requested"?a.push("Request accepted. Watching for newer reports for two minutes\u2026"):s?.status==="complete"?a.push("Family refresh check finished."):s?.status==="send_failed"&&a.push("The family request failed. No refresh is confirmed.");let d=new Map((this._data?.members||[]).map(h=>[h.id,h.name])),p={updated:"Updated",unchanged:"Unchanged",waiting:"Waiting",source_changed:"Tracker changed",ha_updated:"HA updated; GPS report unconfirmed",unsupported:"Refresh unsupported",disabled:"Requests disabled",unavailable:"Unavailable",send_failed:"Request failed",cooldown:"Cooldown",limited:"Daily limit reached",busy:"Provider busy",not_allowed:"Permission required"};for(let h of s?.members||[])d.has(h.id)&&a.push(`${d.get(h.id)}: ${p[h.status]||"Unavailable"}${h.trackers?.length>1?` (${h.trackers.map(f=>`${f.provider}: ${p[f.status]||"Unavailable"}`).join("; ")})`:""}`);this._familyFeedback.textContent=a.join(" \xB7 ")}_render(){if(!this._shell)return;this._updateFamilyFeedback(),this._updateLocationFeedback();let s=this.shadowRoot.activeElement?.dataset?.focus;if(this._title.textContent=is(this._config.title),this._overview.setAttribute("aria-pressed",String(this._mode==="overview")),this._categories.replaceChildren(),this._members.replaceChildren(),this._cityCredit.hidden=!this._data?.city_lookup_enabled,this._providerAlerts.replaceChildren(),!this._data){this._status.textContent=this._error||"Connecting to HomeCircle\u2026",this._mapNote.textContent="Household details appear after an authenticated connection.",this._expanded.replaceChildren();return}let a=Bi(this._data,this._config.hidden_members);!["overview","items",...Ce].includes(this._mode)&&!a.some(h=>h.id===this._mode)&&(this._mode="overview"),this._overview.setAttribute("aria-pressed",String(this._mode==="overview"));let d=jt[this._mode]||a.find(h=>h.id===this._mode)?.name,p=oo(a,this._mode,this._data.focus_ids);if(this._status.replaceChildren(x("div",null,this._emptyCategoryMessage()||(this._mode==="overview"?`Everyone \xB7 ${p.length} of ${a.length} members shown on map`:`${d} \xB7 ${p.length} map ${p.length===1?"position":"positions"}${this._mode==="home"?" \xB7 Primary house only":""}`))),this._error&&this._status.prepend(x("div","connection-warning",this._error)),this._mode==="overview"){let h=a.filter(g=>g.map_visible===!1&&g.focusable&&g.location),f=a.filter(g=>!g.focusable||!g.location);h.length&&this._status.append(x("div","map-visibility-note",`Hidden from Everyone: ${h.map(g=>g.name).join(", ")}`)),f.length&&this._status.append(x("div","map-visibility-note",`No usable map position: ${f.map(g=>g.name).join(", ")}`))}for(let h of this._data.provider_alerts||[]){let f=no(h);f&&this._providerAlerts.append(x("div","provider-alert",f))}for(let h of[...Ce,...this._data.counts?.items?["items"]:[]]){let f=Pt("",()=>this._choose(h),"category");f.dataset.focus=h,f.setAttribute("aria-pressed",String(this._mode===h));let g=a.filter(P=>h==="items"?P.kind==="item":P.kind!=="item"&&P.presence===h).length;f.setAttribute("aria-label",`${jt[h]}: ${g}`),f.append(x("span","count",g),x("span","label",jt[h])),this._categories.append(f)}for(let h of a){let f=x("div","member-entry"),g=x("button","member");g.type="button",g.setAttribute("aria-description","Tap to focus on map. Press and hold for details.");let P,_,C,j=!1,Z=()=>{clearTimeout(P),P=null};g.addEventListener("pointerdown",y=>{y.button===0&&(_=y.clientX,C=y.clientY,Z(),P=setTimeout(()=>{P=null,g.isConnected&&(j=!0,this._openMemberDetails(h.id,g),setTimeout(()=>{j=!1},1e3))},600))}),g.addEventListener("pointermove",y=>{Math.hypot(y.clientX-_,y.clientY-C)>12&&Z()});for(let y of["pointerup","pointercancel","pointerleave"])g.addEventListener(y,Z);g.addEventListener("contextmenu",y=>{y.preventDefault(),Z(),j=!0,this._openMemberDetails(h.id,g),setTimeout(()=>{j=!1},1e3)}),g.addEventListener("click",y=>{if(j){j=!1,y.preventDefault();return}this._choose(h.id)}),g.dataset.focus=h.id,g.setAttribute("aria-pressed",String(this._mode===h.id));let w=x("div"),z=x("div","member-heading");z.append(x("div","name",h.name),x("span",`badge ${h.presence}`,`${h.kind==="pet"?"Pet \xB7 ":h.kind==="item"?"Item \xB7 ":""}${jt[h.presence]}`)),w.append(z);let q=x("div","member-facts");h.place&&!(h.presence==="home"&&h.place.toLowerCase()==="home")&&q.append(x("span","place",`At ${h.place}`));let D=so(h);if(D&&q.append(x("span","place address",D)),Number.isFinite(h.battery)&&h.battery>=0&&h.battery<=100){let y=h.battery<=20&&h.charging!==!0;q.append(x("span",`battery${y?h.battery<=10?" low critical":" low":""}`,`${y?"Low battery":"Battery"} ${h.battery}%${h.charging===!0?" \xB7 charging":""}`))}if(h.battery==null&&Te(h)!=="Unknown"){let y=["low","very_low"].includes(h.battery_status?.value);q.append(x("span",`battery${y?" low":""}`,`Battery ${Te(h)}`))}q.childElementCount&&w.append(q);let A=ao(h,this._hass?.states,this._hass?.config?.time_zone),X=x("div","location-since",A.text);X.title=A.title,w.append(X),h.driving.value===!0&&h.driving.status!=="current"&&w.append(x("span","driving-note",h.driving.status==="last_reported"?"Driving last reported (stale)":"Driving report time unknown"));let F=h.location?.evidence?.freshness==="stale";g.classList.toggle("stale",F),g.classList.toggle("attention",h.presence==="unavailable"||!h.location||h.issues?.some(y=>y.includes("conflict"))===!0);let yt=x("div","report-lines");for(let y of Ke(h))yt.append(x("span",`report-part ${y.kind}`,y.text));w.append(yt),g.append(te(h,"avatar"),w);let ct=Pt("",()=>this._openMemberDetails(h.id,ct),"member-details-button"),b=document.createElementNS("http://www.w3.org/2000/svg","svg");b.setAttribute("viewBox","0 0 24 24"),b.setAttribute("aria-hidden","true"),b.setAttribute("focusable","false");let H=document.createElementNS("http://www.w3.org/2000/svg","path");H.setAttribute("d","M12 11v5"),H.setAttribute("fill","none"),H.setAttribute("stroke","currentColor"),H.setAttribute("stroke-width","2"),H.setAttribute("stroke-linecap","round");let T=document.createElementNS("http://www.w3.org/2000/svg","circle");T.setAttribute("cx","12"),T.setAttribute("cy","8"),T.setAttribute("r","1"),T.setAttribute("fill","currentColor");let M=document.createElementNS("http://www.w3.org/2000/svg","circle");M.setAttribute("cx","12"),M.setAttribute("cy","12"),M.setAttribute("r","9"),M.setAttribute("fill","none"),M.setAttribute("stroke","currentColor"),M.setAttribute("stroke-width","1.8"),b.append(M,H,T),ct.append(b),ct.setAttribute("aria-label",`Details for ${h.name}`),ct.title=`Details for ${h.name}`,f.append(g,ct),this._members.append(f)}a.length||this._members.append(x("div","empty","No members selected for this card.")),this._updateMap(p),s&&[...this.shadowRoot.querySelectorAll("button[data-focus]")].find(h=>h.dataset.focus===s)?.focus({preventScroll:!0})}_updateMap(s){if(!this._map){this._hasMapView=!1,this._map=_t.map(this._mapNode,{zoomControl:!1,minZoom:0,maxZoom:19,scrollWheelZoom:!1,attributionControl:!0}).setView([0,0],2);let h=new _t.Control({position:"topleft"});h.onAdd=()=>{let g=x("div","leaflet-control-zoom leaflet-bar");this._zoomInButton=Pt("+",()=>this._zoomCentered(1),"leaflet-control-zoom-in"),this._zoomOutButton=Pt("\u2212",()=>this._zoomCentered(-1),"leaflet-control-zoom-out"),this._zoomInButton.setAttribute("aria-label","Zoom in"),this._zoomOutButton.setAttribute("aria-label","Zoom out"),this._zoomInButton.title="Zoom in and center markers",this._zoomOutButton.title="Zoom out and center markers",this._recenterButton=Pt("",()=>{this._fit=!0,this._updateMap(this._points||[])},"map-recenter");let P=document.createElementNS("http://www.w3.org/2000/svg","svg");P.setAttribute("viewBox","0 0 24 24"),P.setAttribute("aria-hidden","true");let _=document.createElementNS("http://www.w3.org/2000/svg","path");_.setAttribute("d","M12 3v3m0 12v3M3 12h3m12 0h3M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0"),_.setAttribute("fill","none"),_.setAttribute("stroke","currentColor"),_.setAttribute("stroke-width","2"),_.setAttribute("stroke-linecap","round");let C=document.createElementNS("http://www.w3.org/2000/svg","circle");return C.setAttribute("cx","12"),C.setAttribute("cy","12"),C.setAttribute("r","2"),C.setAttribute("fill","currentColor"),P.append(_,C),this._recenterButton.append(P),this._recenterButton.setAttribute("aria-label","Recenter selected locations"),this._recenterButton.title="Recenter selected locations",g.append(this._zoomInButton,this._zoomOutButton),_t.DomEvent.disableClickPropagation(g),_t.DomEvent.disableScrollPropagation(g),g},h.addTo(this._map);let f=new _t.Control({position:"topleft"});f.onAdd=()=>(_t.DomEvent.disableClickPropagation(this._recenterButton),_t.DomEvent.disableScrollPropagation(this._recenterButton),this._recenterButton),f.addTo(this._map),this._map.on("zoomend zoomlevelschange",()=>this._syncZoomControls()),this._syncZoomControls(),this._layer=_t.layerGroup().addTo(this._map),this._map.on("zoomend moveend",()=>this._markers()),this._resize=new ResizeObserver(()=>{this._resizeHandle?.setAttribute("aria-valuenow",String(Math.round(this._mapNode.getBoundingClientRect().height))),this._map?.invalidateSize({pan:!1}),this._fit&&this._points?.length&&this._updateMap(this._points)}),this._resize.observe(this._mapNode),this._updateTiles(),this._radarController?.sync()}let a=s.find(h=>h.id===this._mode),d=a?[a.id,a.location.latitude,a.location.longitude]:null,p=d&&(!this._followLocation||d.some((h,f)=>h!==this._followLocation[f]));if(this._followLocation=d,s.length&&!this._hasMapView&&(this._fit=!0),this._recenterButton&&(this._recenterButton.disabled=!s.length),this._points=s,this._updateMapNote(),this._fit){let h=this._map.getSize();if(h.x>24&&h.y>24){if(s.length&&this._data&&!["overview","items",...Ce].includes(this._mode)){let f=s[0].location;this._map.setView([f.latitude,f.longitude],Math.min(this._map.getMaxZoom(),17),{animate:!1})}else s.length&&this._map.fitBounds(s.map(f=>[f.location.latitude,f.location.longitude]),{...lo(h),maxZoom:14,animate:!1});this._fit=!1,s.length&&(this._hasMapView=!0)}}else p&&this._map.panTo(d.slice(1),{animate:!1});this._markers()}_syncZoomControls(){!this._map||!this._zoomInButton||(this._zoomInButton.disabled=this._map.getZoom()>=this._map.getMaxZoom(),this._zoomOutButton.disabled=this._map.getZoom()<=this._map.getMinZoom())}_zoomCentered(s){if(!this._map)return;let a=this._map,d=Math.max(a.getMinZoom(),Math.min(a.getMaxZoom(),a.getZoom()+s));if(d===a.getZoom())return;let p=a.getCenter(),h=a.getSize(),f=Ye(this._points||[],g=>a.latLngToContainerPoint([g.latitude,g.longitude])).filter(g=>{let[P,_]=g.members.length>1?[90,108]:[54,68];return g.point.x+P/2>0&&g.point.x-P/2<h.x&&g.point.y>0&&g.point.y-_<h.y}).flatMap(g=>g.members);if(f.length){let P=Ye(f,_=>a.project([_.latitude,_.longitude],d)).map(_=>{let C=a.project([_.members[0].location.latitude,_.members[0].location.longitude],d),[j,Z]=_.members.length>1?[90,108]:[54,68];return{left:C.x-j/2,right:C.x+j/2,top:C.y-Z,bottom:C.y}});p=a.unproject([(Math.min(...P.map(_=>_.left))+Math.max(...P.map(_=>_.right)))/2,(Math.min(...P.map(_=>_.top))+Math.max(...P.map(_=>_.bottom)))/2],d)}this._fit=!1,a.setView(p,d,{animate:!1})}_heightPreferenceKey(){return`homecircle-height:${window.location.pathname}:${this._config.title}`}_applyMapHeight(){if(!this._mapWrap)return;let s=Math.max(220,window.innerHeight-200);this._mapHeight!==null&&this._mapHeight!==void 0&&(this._mapHeight=Math.round(Math.max(220,Math.min(s,this._mapHeight)))),this._mapWrap.classList.toggle("resized",this._mapHeight!=null),this._mapHeight==null?this._mapWrap.style.removeProperty("--map-height"):this._mapWrap.style.setProperty("--map-height",`${this._mapHeight}px`),this._resizeHandle?.setAttribute("aria-valuemin","220"),this._resizeHandle?.setAttribute("aria-valuemax",String(s)),this._resizeHandle?.setAttribute("aria-valuenow",String(this._mapHeight??Math.round(this._mapNode.getBoundingClientRect().height))),this._map?.invalidateSize({animate:!1,debounceMoveend:!0})}_saveMapHeight(){try{this._mapHeight==null?window.localStorage.removeItem(this._heightPreferenceKey()):window.localStorage.setItem(this._heightPreferenceKey(),String(this._mapHeight))}catch{}}_finishMapResize(s){let a=this._mapDrag;a&&(this._mapDrag=null,s?this._saveMapHeight():(this._mapHeight=a.previous,this._applyMapHeight()),this._resizeHandle?.hasPointerCapture?.(a.id)&&this._resizeHandle.releasePointerCapture(a.id))}_mapPreferenceKey(){return`homecircle-map:${window.location.pathname}:${this._config.title}:${this._config.map_tiles}`}_syncMapControls(){this._mapControls&&(this._mapControls.hidden=this._config.map_tiles==="none",this._streetButton.setAttribute("aria-pressed",String(this._mapBackground==="osm")),this._satelliteButton.setAttribute("aria-pressed",String(this._mapBackground==="satellite")))}_setMapBackground(s){if(!(this._config.map_tiles==="none"||!["osm","satellite"].includes(s)||s===this._mapBackground)){this._mapBackground=s;try{window.localStorage.setItem(this._mapPreferenceKey(),s)}catch{}this._syncMapControls(),this._updateTiles(),this._updateMapNote()}}_updateTiles(){if(!this._map||(this._tiles&&(this._map.removeLayer(this._tiles),this._tiles.off(),this._tiles=null),this._tileCycleFailed=this._tileUnavailable=!1,this._config.map_tiles==="none"))return;let s=this._mapBackground==="satellite",a=_t.tileLayer(s?"https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}":"https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,maxNativeZoom:s?16:19,attribution:s?'<a href="https://www.usgs.gov/the-national-map-data-delivery" target="_blank" rel="noopener">USDA, USGS The National Map: Orthoimagery</a>':'\xA9 <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',referrerPolicy:"strict-origin-when-cross-origin"});this._tiles=a,a.on("loading",()=>{this._tiles===a&&(this._tileCycleFailed=!1)}),a.on("tileerror",()=>{this._tiles===a&&(this._tileCycleFailed=this._tileUnavailable=!0,this._updateMapNote())}),a.on("load",()=>{this._tiles===a&&(this._tileUnavailable=!!this._tileCycleFailed,this._updateMapNote())}),a.addTo(this._map)}_emptyCategoryMessage(){let s={away:"No one is away.",driving:"No one is currently reported as driving.",unavailable:"Everyone has available presence information."};return!s[this._mode]||!this._data||Bi(this._data,this._config.hidden_members).some(d=>d.presence===this._mode)?null:s[this._mode]}_updateMapNote(){this._mapNote&&(this._mapNote.textContent=this._emptyCategoryMessage()?"Select Everyone to restore the household overview.":this._points?.length?this._tileUnavailable?`${this._mapBackground==="satellite"?"Satellite":"Street"} tiles unavailable. Presence and markers still work.`:this._config.map_tiles!=="none"?this._mapBackground==="satellite"?"Satellite \xB7 USGS imagery \xB7 U.S. detail; limited elsewhere":"Street map \xB7 select a marker or member":"Private map \xB7 external tiles off \xB7 enable in card settings":"No map position shown for this selection. Presence counts are unchanged.")}_markers(){if(!this._map||!this._layer)return;let s=this.shadowRoot.activeElement?.dataset?.focus;this._layer.clearLayers(),this._expanded.replaceChildren();for(let a of Ye(this._points||[],d=>this._map.latLngToContainerPoint([d.latitude,d.longitude]))){let d=a.members,p=d[0],h=Pt("",_=>{if(d.length===1)this._chooseFromMap(p.id,_);else{this._expandedIds=d.map(C=>C.id);for(let C of this._mapNode.querySelectorAll('[data-focus^="cluster:"]'))C.setAttribute("aria-expanded",String(C===h));this._showGroup(d),this._expanded.querySelector("button")?.focus()}},d.length>1?"group":"");if(d.length>1){let _=x("span",`marker-portraits count-${Math.min(d.length,4)}`);for(let C of d.slice(0,4))_.append(te(C));d.length>4&&_.append(x("span","marker-overflow",`+${d.length-4}`)),h.append(_)}else h.append(te(p));let f=d.map(_=>_.id).join("|");d.length>1?(h.dataset.focus=`cluster:${f}`,h.setAttribute("aria-expanded",String(this._expandedIds?.join("|")===f))):(h.dataset.focus=`marker:${p.id}`,h.setAttribute("aria-pressed",String(this._mode===p.id))),this._expandedIds?.join("|")===f&&this._showGroup(d),h.setAttribute("aria-label",d.length>1?`${d.map(_=>_.name).join(", ")} at this location. Expand to choose.`:p.name);let g=d.length>1?[90,108]:[54,68],P=_t.divIcon({html:h,className:"marker",iconSize:g,iconAnchor:[g[0]/2,g[1]]});_t.marker([p.location.latitude,p.location.longitude],{icon:P,keyboard:!1}).addTo(this._layer)}if(s?.startsWith("marker:")||s?.startsWith("group:")||s?.startsWith("cluster:")){let a=[...this._mapNode.querySelectorAll("[data-focus]"),...this._expanded.querySelectorAll("[data-focus]"),...this._members.querySelectorAll("[data-focus]")],d=s.slice(s.indexOf(":")+1).split("|");(a.find(h=>h.dataset.focus===s)||a.find(h=>h.dataset.focus?.startsWith("cluster:")&&d.some(f=>h.dataset.focus.slice(8).split("|").includes(f)))||a.find(h=>d.some(f=>h.dataset.focus===`marker:${f}`))||a.find(h=>d.includes(h.dataset.focus)))?.focus({preventScroll:!0})}}_showGroup(s){this._expanded.replaceChildren(x("span","subtle","Choose a member at this location:"));for(let a of s){let d=Pt(a.name,p=>this._chooseFromMap(a.id,p));d.dataset.focus="group:"+a.id,this._expanded.append(d)}}_destroyMap(){this._radarController?.dispose(),this._resize?.disconnect(),this._map?.remove(),this._map=null,this._layer=null,this._tiles=null,this._zoomInButton=this._zoomOutButton=null,this._tileCycleFailed=this._tileUnavailable=!1,this._points=[],this._pointKey=null,this._expandedIds=null}},Di=class extends HTMLElement{constructor(){super(),this._generation=0,this._refreshToken=0,this.attachShadow({mode:"open"})}setConfig(s){this._config=Oi(s),this._render()}disconnectedCallback(){this._generation++,this._members=null,this._loaded=!1,this.shadowRoot.replaceChildren()}set hass(s){if((this._connection!==s.connection||s.connected===!1)&&(this._generation++,this._loaded=!1,this._members=null,this._connection=s.connection,this._render()),!this._loaded&&s.connected!==!1){this._loaded=!0;let a=++this._generation;s.callWS({type:"homecircle/snapshot"}).then(d=>{a!==this._generation||!this.isConnected||(this._members=d.members.map(p=>({id:p.id,name:p.name})),this._render())}).catch(()=>{a===this._generation&&(this._loaded=!1,this._members=null,this._render())})}}_change(s){this._config={...this._config,...s},this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_render(){if(!this._config)return;this.shadowRoot.replaceChildren();let s=x("style");s.textContent=Ai;let a=x("div","editor"),d=x("label","","Title"),p=x("input");p.type="text",p.value=this._config.title,p.addEventListener("change",()=>this._change({title:p.value})),d.append(p),a.append(d);let h=x("label","","Map background"),f=x("select");for(let[Z,w]of[["none","Private \xB7 no external tiles"],["osm","Street \xB7 OpenStreetMap"],["satellite","Satellite \xB7 USGS imagery (U.S. detail)"]]){let z=x("option","",w);z.value=Z,f.append(z)}f.value=this._config.map_tiles,f.addEventListener("change",()=>this._change({map_tiles:f.value})),h.append(f),a.append(h),a.append(x("p","","Street is the default. Satellite uses USGS aerial and satellite imagery, with detailed coverage in the U.S. and limited detail elsewhere. Images are historical, not live. Tile requests send the viewed map area, your network address, and site origin to the selected service. No names or HA credentials are sent. Choose Private to turn external tiles off. Availability is best effort."));let g=x("a","","OpenStreetMap privacy policy");g.href="https://osmfoundation.org/wiki/Privacy_Policy",g.target="_blank",g.rel="noopener",a.append(g);let P=x("a","","USGS imagery information");P.href="https://www.usgs.gov/the-national-map-data-delivery",P.target="_blank",P.rel="noopener",a.append(P);let _=x("label","check"),C=x("input");C.type="checkbox",C.checked=this._config.fill_screen,C.addEventListener("change",()=>this._change({fill_screen:C.checked})),_.append(C,x("span","","Fill wall display height")),a.append(_),a.append(x("p","","Use with a dedicated full-width dashboard view. The map expands to use the space below this card's top edge."));let j=x("fieldset");j.append(x("legend","","Visible members"));for(let Z of this._members||[]){let w=x("label","check"),z=x("input");z.type="checkbox",z.checked=!this._config.hidden_members.includes(Z.id),z.addEventListener("change",()=>{let q=new Set(this._config.hidden_members);z.checked?q.delete(Z.id):q.add(Z.id),this._change({hidden_members:[...q]})}),w.append(z,x("span","",Z.name)),j.append(w)}a.append(j,x("p","","Visibility applies to this card only. HA user permissions control access. Configure household sources in Settings \u2192 Devices & services \u2192 HomeCircle.")),this.shadowRoot.append(s,a)}};customElements.get("homecircle-card")||customElements.define("homecircle-card",Hi);customElements.get("homecircle-card-editor")||customElements.define("homecircle-card-editor",Di);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="homecircle-card")||window.customCards.push({type:"homecircle-card",name:"HomeCircle",description:"Household presence and map controls, with a Private background option.",preview:!0});
/*! Bundled license information:

leaflet/dist/leaflet-src.js:
  (* @preserve
   * Leaflet 1.9.4, a JS library for interactive maps. https://leafletjs.com
   * (c) 2010-2023 Vladimir Agafonkin, (c) 2010-2011 CloudMade
   *)
*/
