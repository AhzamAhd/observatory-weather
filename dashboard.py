import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import os
os.environ["PYTHONWARNINGS"] = "ignore:DeprecationWarning"
from comet_tracker import (get_current_comets,
                            get_comet_visibility,
                            magnitude_to_visibility,
                            comet_type_info)

from reviews import (add_review, get_reviews,
                     get_observatory_stats,
                     get_top_rated_observatories,
                     get_recent_reviews,
                     get_rating_distribution,
                     stars, rating_color)
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
import streamlit as st
import streamlit.components.v1 as components
import json
import math
import sqlite3
import pandas as pd
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from streamlit_folium import st_folium
from observing_window import get_all_windows
from object_visibility import (get_best_observatories_for_object,
                                calculate_visibility, OBJECTS,
                                get_ephem_object)
from peak_time import get_all_peak_times, calculate_hourly_scores
from atmospheric import get_full_atmospheric_analysis
from historical_reliability import (calculate_reliability_scores,
                                     get_grade_color,
                                     get_trend_emoji)
from site_comparison import compare_sites
from semester_planning import build_calendar_data, get_best_months
import calendar
from educational_mode import (get_all_concepts,
                               get_concepts_by_category)
from sheets_subscriptions import (add_subscription,
                                   remove_subscription,
                                   load_subscriptions)
from telescope_efficiency import get_all_efficiency_scores
from snr_calculator import (calculate_snr, get_snr_for_all_observatories,
                              TELESCOPE_SPECS, OBJECT_MAGNITUDES,
                              get_sky_brightness, PHOTOMETRIC_FILTERS)
from airmass_calculator import (
    get_object_airmass_curve,
    compare_objects_airmass,
    get_best_observation_window,
    altitude_to_airmass,
    airmass_quality,
    airmass_color,
    extinction_magnitudes
)
from meteor_showers import (get_all_showers_sorted,
                             get_active_showers,
                             get_upcoming_showers,
                             get_year_calendar,
                             moon_phase_on_peak,
                             observing_score,
                             get_zhr_quality,
                             get_speed_rating)
from sky_chart import compute_sky
from satellite_tracker import (get_all_passes,
                                get_iss_tle,
                                calculate_passes,
                                get_current_position,
                                magnitude_visibility,
                                magnitude_emoji)
from asteroid_tracker import (fetch_asteroids,
                               fetch_asteroids_range,
                               get_asteroid_stats,
                               format_distance,
                               classify_size,
                               size_comparison,
                               estimate_impact_energy,
                               assess_threat)

from eclipses import (get_upcoming_events,
                      get_eclipse_visibility,
                      get_best_observatories_for_eclipse,
                      eclipse_rarity,
                      get_all_past_recent,
                      SOLAR_ECLIPSES,
                      LUNAR_ECLIPSES,
                      TRANSITS)
from forecast import fetch_forecast, get_daily_summary
from precompute import load_precomputed, load_precomputed_raw

from PIL import Image as _Image
_favicon = _Image.open("gowc_logo.png")
st.set_page_config(
    page_title="GOWC - Observatory Weather Tracker",
    page_icon=_favicon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── PWA manifest + meta tags injected into <head> ─────────────────
import base64, pathlib

def _img_to_b64(path):
    try:
        return base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    except Exception:
        return ""

_icon192 = _img_to_b64("assets/icons/icon-192.png")
_icon512 = _img_to_b64("assets/icons/icon-512.png")

_manifest = f"""{{
  "name": "GOWC — Global Observatory Weather Tracker",
  "short_name": "GOWC",
  "description": "Real-time weather intelligence for astronomers worldwide",
  "start_url": "/",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#08090f",
  "theme_color": "#00b4d8",
  "icons": [
    {{"src": "data:image/png;base64,{_icon192}", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"}},
    {{"src": "data:image/png;base64,{_icon512}", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}}
  ]
}}"""

_manifest_b64 = base64.b64encode(_manifest.encode()).decode()

# Inject PWA manifest, head meta tags (incl. OpenGraph/Twitter) and the
# service worker into the PARENT document head via a 0-height component.
# st.markdown sanitises <meta>/<script>, so we build the head nodes in JS.
_OG_IMG = "https://raw.githubusercontent.com/AhzamAhd/observatory-weather/main/assets/gowc_banner.png"
_HEAD_TAGS = [
    ("link", {"rel": "manifest", "href": f"data:application/manifest+json;base64,{_manifest_b64}"}),
    ("meta", {"name": "mobile-web-app-capable", "content": "yes"}),
    ("meta", {"name": "apple-mobile-web-app-capable", "content": "yes"}),
    ("meta", {"name": "apple-mobile-web-app-status-bar-style", "content": "black-translucent"}),
    ("meta", {"name": "apple-mobile-web-app-title", "content": "GOWC"}),
    ("meta", {"name": "theme-color", "content": "#00b4d8"}),
    ("meta", {"name": "application-name", "content": "GOWC"}),
    ("link", {"rel": "apple-touch-icon", "href": f"data:image/png;base64,{_icon192}"}),
    ("meta", {"name": "description", "content": "Real-time weather intelligence for astronomers worldwide — observing conditions, seeing, airmass and SNR for 1,163 observatories."}),
    ("meta", {"property": "og:type", "content": "website"}),
    ("meta", {"property": "og:site_name", "content": "GOWC"}),
    ("meta", {"property": "og:title", "content": "GOWC — Global Observatory Weather Tracker"}),
    ("meta", {"property": "og:description", "content": "Real-time weather intelligence for astronomers worldwide — observing conditions, seeing, airmass and SNR for 1,163 observatories."}),
    ("meta", {"property": "og:url", "content": "https://gowcastroclimate.com"}),
    ("meta", {"property": "og:image", "content": _OG_IMG}),
    ("meta", {"property": "og:image:width", "content": "1243"}),
    ("meta", {"property": "og:image:height", "content": "357"}),
    ("meta", {"name": "twitter:card", "content": "summary_large_image"}),
    ("meta", {"name": "twitter:title", "content": "GOWC — Global Observatory Weather Tracker"}),
    ("meta", {"name": "twitter:description", "content": "Real-time observing conditions, seeing, airmass and SNR for 1,163 observatories worldwide."}),
    ("meta", {"name": "twitter:image", "content": _OG_IMG}),
]
components.html(
    f"""
<script>
(function() {{
  var doc = window.parent.document;
  var tags = {json.dumps(_HEAD_TAGS)};
  tags.forEach(function(t) {{
    var sel = t[0] + Object.keys(t[1]).map(function(k) {{
      return '[' + k + '="' + t[1][k].replace(/"/g, '\\\\"') + '"]';
    }}).join('');
    try {{ if (doc.head.querySelector(t[0] + (t[1].property ? '[property="'+t[1].property+'"]' : t[1].name ? '[name="'+t[1].name+'"]' : ''))) return; }} catch(e) {{}}
    var el = doc.createElement(t[0]);
    for (var k in t[1]) el.setAttribute(k, t[1][k]);
    doc.head.appendChild(el);
  }});
  if ('serviceWorker' in window.parent.navigator) {{
    var sw = "self.addEventListener('install',e=>self.skipWaiting());"
           + "self.addEventListener('activate',e=>clients.claim());"
           + "self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));";
    var blob = new Blob([sw], {{type:'application/javascript'}});
    window.parent.navigator.serviceWorker.register(URL.createObjectURL(blob), {{scope:'/'}}).catch(function(){{}});
  }}
}})();
</script>
""",
    height=0,
)

svg = '''<svg width="1440" height="900" viewBox="0 0 1440 900" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="1440" height="900" fill="#020810"/>
  <circle cx="18" cy="22" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="55" cy="8" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="92" cy="38" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="165" cy="48" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="238" cy="55" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="312" cy="42" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="385" cy="52" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="458" cy="8" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="532" cy="18" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="605" cy="12" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="678" cy="22" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="752" cy="8" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="825" cy="18" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="898" cy="12" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="972" cy="22" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="1045" cy="8" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1118" cy="18" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="1192" cy="12" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="1265" cy="22" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="1338" cy="8" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1412" cy="18" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="38" cy="105" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="82" cy="132" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="168" cy="138" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="255" cy="142" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="342" cy="135" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="428" cy="132" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="515" cy="138" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="602" cy="135" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="688" cy="132" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="775" cy="142" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="862" cy="135" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="948" cy="132" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1035" cy="142" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="1122" cy="135" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="1208" cy="132" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1295" cy="142" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="1382" cy="135" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="22" cy="198" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="72" cy="222" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="172" cy="228" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="272" cy="232" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="372" cy="222" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="472" cy="228" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="572" cy="232" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="672" cy="222" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="772" cy="228" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="872" cy="232" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="972" cy="222" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="1072" cy="228" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="1172" cy="232" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="1272" cy="222" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="1372" cy="228" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="45" cy="302" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="105" cy="325" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="225" cy="328" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="345" cy="332" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="465" cy="325" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="585" cy="328" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="705" cy="332" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="825" cy="325" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="945" cy="328" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1065" cy="332" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="1185" cy="325" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="1305" cy="328" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1425" cy="332" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="28" cy="402" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="98" cy="428" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="238" cy="432" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="378" cy="435" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="518" cy="428" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="658" cy="432" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="798" cy="435" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="938" cy="428" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="1078" cy="432" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="1218" cy="435" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="1358" cy="428" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="55" cy="502" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="135" cy="528" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="295" cy="532" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="455" cy="532" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="615" cy="528" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="775" cy="532" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="935" cy="532" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="1095" cy="528" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="1255" cy="532" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1415" cy="532" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="38" cy="602" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="118" cy="628" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="278" cy="632" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="438" cy="635" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="598" cy="628" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="758" cy="632" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="918" cy="635" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="1078" cy="628" r="0.6" fill="#fff" opacity="0.58"/>
  <circle cx="1238" cy="632" r="0.5" fill="#fff" opacity="0.52"/>
  <circle cx="1398" cy="635" r="0.4" fill="#fff" opacity="0.44"/>
  <circle cx="62" cy="702" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="152" cy="728" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="332" cy="732" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="512" cy="732" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="692" cy="728" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="872" cy="732" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="1052" cy="732" r="0.4" fill="#fff" opacity="0.42"/>
  <circle cx="1232" cy="728" r="0.6" fill="#fff" opacity="0.56"/>
  <circle cx="1412" cy="732" r="0.5" fill="#fff" opacity="0.5"/>
  <circle cx="48" cy="802" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="148" cy="828" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="348" cy="832" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="548" cy="832" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="748" cy="828" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="948" cy="832" r="0.5" fill="#fff" opacity="0.48"/>
  <circle cx="1148" cy="832" r="0.4" fill="#fff" opacity="0.4"/>
  <circle cx="1348" cy="828" r="0.6" fill="#fff" opacity="0.55"/>
  <circle cx="88" cy="872" r="0.5" fill="#fff" opacity="0.45"/>
  <circle cx="208" cy="888" r="0.6" fill="#fff" opacity="0.5"/>
  <circle cx="448" cy="888" r="0.5" fill="#fff" opacity="0.45"/>
  <circle cx="688" cy="888" r="0.4" fill="#fff" opacity="0.38"/>
  <circle cx="928" cy="888" r="0.6" fill="#fff" opacity="0.5"/>
  <circle cx="1168" cy="888" r="0.5" fill="#fff" opacity="0.45"/>
  <circle cx="1408" cy="888" r="0.4" fill="#fff" opacity="0.38"/>
  <circle cx="145" cy="65" r="1.2" fill="#fff" opacity="0.75"/>
  <circle cx="388" cy="90" r="1" fill="#fff" opacity="0.68"/>
  <circle cx="632" cy="48" r="1.4" fill="#fff" opacity="0.8"/>
  <circle cx="875" cy="85" r="1" fill="#fff" opacity="0.68"/>
  <circle cx="1118" cy="58" r="1.2" fill="#fff" opacity="0.75"/>
  <circle cx="1362" cy="92" r="1" fill="#fff" opacity="0.68"/>
  <circle cx="75" cy="262" r="1.2" fill="#fff" opacity="0.7"/>
  <circle cx="642" cy="248" r="1.4" fill="#fff" opacity="0.78"/>
  <circle cx="1208" cy="258" r="1.2" fill="#fff" opacity="0.7"/>
  <circle cx="112" cy="452" r="1.2" fill="#fff" opacity="0.68"/>
  <circle cx="722" cy="448" r="1.4" fill="#fff" opacity="0.75"/>
  <circle cx="1332" cy="452" r="1.2" fill="#fff" opacity="0.68"/>
  <circle cx="192" cy="652" r="1.2" fill="#fff" opacity="0.65"/>
  <circle cx="842" cy="648" r="1.4" fill="#fff" opacity="0.72"/>
  <circle cx="252" cy="852" r="1.2" fill="#fff" opacity="0.62"/>
  <circle cx="952" cy="848" r="1.4" fill="#fff" opacity="0.68"/>
  <g transform="translate(290,158)"><circle r="4" fill="#FFD700" opacity="0.95"/><line x1="0" y1="-12" x2="0" y2="12" stroke="#FFD700" stroke-width="0.9" opacity="0.55"/><line x1="-12" y1="0" x2="12" y2="0" stroke="#FFD700" stroke-width="0.9" opacity="0.55"/></g>
  <g transform="translate(1155,192)"><circle r="4.5" fill="#c8e6ff" opacity="0.92"/><line x1="0" y1="-13" x2="0" y2="13" stroke="#c8e6ff" stroke-width="0.9" opacity="0.52"/><line x1="-13" y1="0" x2="13" y2="0" stroke="#c8e6ff" stroke-width="0.9" opacity="0.52"/></g>
  <g transform="translate(720,85)"><circle r="5" fill="#fff" opacity="0.95"/><line x1="0" y1="-15" x2="0" y2="15" stroke="#fff" stroke-width="1" opacity="0.55"/><line x1="-15" y1="0" x2="15" y2="0" stroke="#fff" stroke-width="1" opacity="0.55"/></g>
  <g transform="translate(98,548)"><circle r="3.5" fill="#FFD700" opacity="0.88"/><line x1="0" y1="-10" x2="0" y2="10" stroke="#FFD700" stroke-width="0.8" opacity="0.48"/><line x1="-10" y1="0" x2="10" y2="0" stroke="#FFD700" stroke-width="0.8" opacity="0.48"/></g>
  <g transform="translate(1352,525)"><circle r="3.5" fill="#ffc8a0" opacity="0.88"/><line x1="0" y1="-10" x2="0" y2="10" stroke="#ffc8a0" stroke-width="0.8" opacity="0.48"/><line x1="-10" y1="0" x2="10" y2="0" stroke="#ffc8a0" stroke-width="0.8" opacity="0.48"/></g>
  <g transform="translate(482,732)"><circle r="3" fill="#c8e6ff" opacity="0.85"/><line x1="0" y1="-9" x2="0" y2="9" stroke="#c8e6ff" stroke-width="0.7" opacity="0.45"/><line x1="-9" y1="0" x2="9" y2="0" stroke="#c8e6ff" stroke-width="0.7" opacity="0.45"/></g>
  <g transform="translate(962,752)"><circle r="3" fill="#FFD700" opacity="0.82"/><line x1="0" y1="-9" x2="0" y2="9" stroke="#FFD700" stroke-width="0.7" opacity="0.42"/><line x1="-9" y1="0" x2="9" y2="0" stroke="#FFD700" stroke-width="0.7" opacity="0.42"/></g>
  <circle cx="322" cy="145" r="2.2" fill="#fff" opacity="0.92"/><circle cx="338" cy="152" r="1.5" fill="#fff" opacity="0.55"/><circle cx="352" cy="158" r="0.8" fill="#fff" opacity="0.25"/>
  <circle cx="1082" cy="262" r="2" fill="#fff" opacity="0.88"/><circle cx="1096" cy="270" r="1.2" fill="#fff" opacity="0.48"/><circle cx="1108" cy="277" r="0.7" fill="#fff" opacity="0.22"/>
  <circle cx="582" cy="625" r="1.8" fill="#aaddff" opacity="0.85"/><circle cx="595" cy="631" r="1.1" fill="#aaddff" opacity="0.45"/><circle cx="606" cy="636" r="0.6" fill="#aaddff" opacity="0.2"/>
  <circle cx="202" cy="472" r="2" fill="#fff" opacity="0.88"/><circle cx="216" cy="479" r="1.2" fill="#fff" opacity="0.45"/><circle cx="228" cy="485" r="0.7" fill="#fff" opacity="0.2"/>
  <circle cx="1242" cy="652" r="1.8" fill="#ffd080" opacity="0.85"/><circle cx="1254" cy="658" r="1.1" fill="#ffd080" opacity="0.42"/><circle cx="1264" cy="663" r="0.6" fill="#ffd080" opacity="0.18"/>
  <circle cx="762" cy="815" r="1.8" fill="#fff" opacity="0.82"/><circle cx="774" cy="821" r="1.1" fill="#fff" opacity="0.42"/><circle cx="784" cy="826" r="0.6" fill="#fff" opacity="0.18"/>
  <g transform="translate(858,328) rotate(28)"><ellipse rx="9" ry="6" fill="#2a3a2a" stroke="#4a6a4a" stroke-width="0.8"/><ellipse rx="5" ry="3" fill="#1e2e1e" opacity="0.7"/><circle cx="3" cy="-2" r="1.5" fill="#3a5a3a" opacity="0.6"/></g>
  <g transform="translate(1292,392) rotate(-15)"><ellipse rx="12" ry="8" fill="#2e2a22" stroke="#5a5040" stroke-width="0.8"/><ellipse rx="7" ry="4" fill="#221e18" opacity="0.7"/><circle cx="4" cy="-3" r="2" fill="#4a4035" opacity="0.6"/></g>
  <g transform="translate(185,732) rotate(42)"><ellipse rx="7" ry="5" fill="#2a2838" stroke="#4a4858" stroke-width="0.8"/><ellipse rx="4" ry="2.5" fill="#1e1c2a" opacity="0.7"/></g>
  <g transform="translate(1085,732) rotate(-32)"><ellipse rx="10" ry="7" fill="#28302a" stroke="#485840" stroke-width="0.8"/><ellipse rx="6" ry="3.5" fill="#1c2420" opacity="0.7"/></g>
  <g transform="translate(615,188) rotate(18)"><ellipse rx="6" ry="4" fill="#2a2820" stroke="#4a4838" stroke-width="0.7"/><ellipse rx="3" ry="2" fill="#1e1c18" opacity="0.7"/></g>
  <g transform="translate(482,552) rotate(-22)"><ellipse rx="8" ry="5" fill="#302828" stroke="#504040" stroke-width="0.8"/><ellipse rx="4.5" ry="2.5" fill="#241c1c" opacity="0.7"/></g>
</svg>'''


# ── Theme ─────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

_t = st.session_state.theme

if _t == "dark":
    # Deep-space dark: cosmic void backgrounds, nebula cyan accent, star gold highlight
    BG          = "#08090f"   # deep void black
    BG2         = "#0e1117"   # dark nebula surface
    BG3         = "#151b26"   # slightly lighter panel
    BORDER      = "#1e2d40"   # subtle blue-tinted border
    TEXT        = "#cdd9e5"   # starlight white
    TEXT2       = "#5c7a96"   # dim stellar blue-grey
    ACCENT      = "#00b4d8"   # nebula cyan
    ACCENT2     = "#90e0ef"   # bright nebula highlight
    GOLD        = "#f4a261"   # warm star gold
    SIDEBAR_BG  = "#05070d"   # darkest void for sidebar
else:
    # Light mode: observatory daytime — warm ivory, deep navy accent
    BG          = "#f4f6fb"
    BG2         = "#ffffff"
    BG3         = "#e8edf5"
    BORDER      = "#c5d0e0"
    TEXT        = "#0d1b2a"
    TEXT2       = "#4a6080"
    ACCENT      = "#0077b6"   # deep observatory navy
    ACCENT2     = "#023e8a"
    GOLD        = "#e07b39"
    SIDEBAR_BG  = "#edf0f7"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Base ── */
    .stApp {{
        background-color: {BG} !important;
        color: {TEXT} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}
    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG} !important;
        border-right: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {TEXT} !important;
    }}

    /* ── Sidebar nav radio ── */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
        gap: 0px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        display: flex !important;
        align-items: center !important;
        padding: 6px 14px !important;
        border-radius: 5px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: {TEXT2} !important;
        cursor: pointer !important;
        transition: none !important;
        animation: none !important;
        letter-spacing: 0.02em !important;
        line-height: 1.4 !important;
        margin: 1px 4px !important;
        border: none !important;
        background: transparent !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        background-color: {BG3} !important;
        color: {TEXT} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background-color: {ACCENT}15 !important;
        color: {ACCENT} !important;
        font-weight: 600 !important;
        border-left: 2px solid {ACCENT} !important;
        padding-left: 12px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {{
        display: none !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {{
        display: none !important;
    }}
    [data-testid="stSidebar"] [data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p {{
        margin: 0 !important;
        font-size: 0.82rem !important;
    }}

    /* ── Hide Streamlit chrome ── */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu, footer {{
        display: none !important;
    }}
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {{
        display: flex !important;
    }}

    /* ── Metric cards ── */
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, {BG2} 0%, {BG3} 100%) !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT2} !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.78rem !important;
    }}

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }}

    /* ── Dividers ── */
    hr {{
        border: none !important;
        border-top: 1px solid {BORDER} !important;
        margin: 1.2rem 0 !important;
        opacity: 0.6 !important;
    }}

    /* ── Headings ── */
    h1 {{
        color: {TEXT} !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}
    h2 {{
        color: {TEXT} !important;
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.005em !important;
        border-bottom: 1px solid {BORDER} !important;
        padding-bottom: 0.4rem !important;
        margin-bottom: 1rem !important;
    }}
    h3 {{
        color: {TEXT} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }}

    /* ── Buttons ── */
    .stButton > button {{
        background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT2}aa 100%) !important;
        color: #ffffff !important;
        border: 1px solid {ACCENT}88 !important;
        border-radius: 7px !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
        padding: 0.45rem 1.1rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 0 10px {ACCENT}33 !important;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {ACCENT2} 0%, {ACCENT} 100%) !important;
        box-shadow: 0 0 16px {ACCENT}55 !important;
    }}

    /* ── Selectbox / radio (non-sidebar) ── */
    [data-testid="stRadio"] label {{
        color: {TEXT} !important;
        font-size: 0.85rem !important;
    }}

    /* ── Captions ── */
    [data-testid="stCaptionContainer"] p {{
        color: {TEXT2} !important;
        font-size: 0.74rem !important;
    }}

    /* ── Progress bars ── */
    [data-testid="stProgressBar"] > div {{
        background: linear-gradient(90deg, {ACCENT} 0%, {ACCENT2} 100%) !important;
        border-radius: 4px !important;
    }}
    [data-testid="stProgressBar"] {{
        background-color: {BG3} !important;
        border-radius: 4px !important;
    }}

    /* ── Tabs (sub-tabs inside pages) ── */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: {BG2} !important;
        border-radius: 8px 8px 0 0 !important;
        border-bottom: 1px solid {BORDER} !important;
        gap: 0 !important;
        padding: 0 8px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {TEXT2} !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        border-bottom: 2px solid transparent !important;
        background: transparent !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {ACCENT} !important;
        border-bottom: 2px solid {ACCENT} !important;
        font-weight: 600 !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        background-color: {BG2} !important;
        border: 1px solid {BORDER} !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        padding: 1rem !important;
    }}

    /* ── Input fields ── */
    .stTextInput input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {{
        background-color: {BG3} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 7px !important;
        color: {TEXT} !important;
    }}
    .stSlider [data-testid="stSlider"] div {{
        color: {TEXT} !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: {TEXT2} !important;
    }}

    /* ── Expander ── */
    [data-testid="stExpander"] {{
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        background-color: {BG2} !important;
        overflow: hidden !important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: {TEXT} !important;
        letter-spacing: 0.01em !important;
    }}

    /* ── Alerts / info boxes ── */
    [data-testid="stAlert"] {{
        border-radius: 9px !important;
        border: 1px solid {BORDER} !important;
        background-color: {BG2} !important;
    }}

    /* ── Spinner ── */
    [data-testid="stSpinner"] {{
        color: {ACCENT} !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {BG2};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {BORDER};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {TEXT2};
    }}
    </style>
""", unsafe_allow_html=True)


def page_header(icon, title, subtitle=""):
    """Consistent styled header bar for every page."""
    _sub = (f'<div style="font-size:0.82rem;color:{TEXT2};'
            f'margin-top:4px;line-height:1.5;">{subtitle}</div>'
            if subtitle else "")
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:16px;
            padding:16px 22px;margin-bottom:18px;border-radius:12px;
            background:linear-gradient(135deg,{BG2} 0%,{BG3} 100%);
            border:1px solid {BORDER};border-left:4px solid {ACCENT};">
  <div style="font-size:1.9rem;line-height:1;flex-shrink:0;">{icon}</div>
  <div style="flex:1;">
    <div style="font-size:1.35rem;font-weight:700;color:{TEXT};
                letter-spacing:0.01em;">{title}</div>
    {_sub}
  </div>
</div>
""", unsafe_allow_html=True)




@st.cache_resource
def get_all_precomputed():
    return {
        "windows":    load_precomputed(
            "observing_windows_slim"),
        "atmospheric": load_precomputed("atmospheric"),
        "peak_times":  load_precomputed("peak_times"),
        "efficiency":  load_precomputed(
            "efficiency_optical")
    }
@st.cache_data(ttl=3600)  # cache for 1 hour
def load_atmospheric():
    from atmospheric import get_full_atmospheric_analysis
    df      = load_data()
    results = []
    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis({
            "temperature_c":    row["temperature_c"],
            "wind_speed_ms":    row["wind_speed_ms"],
            "humidity_pct":     row["humidity_pct"],
            "altitude_m":       row["altitude_m"],
            "surface_pressure": row.get("surface_pressure"),
            "jet_stream_ms":    row.get("jet_stream_ms"),
            "latitude":         row["latitude"]
        })
        results.append({
            "observatory":  row["observatory"],
            "country":      row["country"],
            "altitude_m":   row["altitude_m"],
            "weather_score": row["observation_score"],
            **atm
        })
    return pd.DataFrame(results).sort_values(
        "seeing_arcsec", ascending=True)

@st.cache_data(ttl=3600)
def load_data():
    from db import query_df
    # DISTINCT ON keeps only the latest reading per observatory,
    # reducing result set from 1163 to ~300 rows (22x faster).
    _df = query_df("""
        SELECT DISTINCT ON (o.id)
            o.name         AS observatory,
            o.country,
            o.latitude,
            o.longitude,
            o.altitude_m,
            o.mpc_code,
            w.fetch_date,
            w.fetch_time,
            w.fetch_datetime,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.precipitation_mm,
            w.surface_pressure,
            w.jet_stream_ms,
            ROUND(GREATEST(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0
                   ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0
                   ELSE 0 END)
            )::numeric, 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 40 THEN 'Marginal'
                ELSE 'Poor'
            END AS condition
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        WHERE w.fetch_date = (
            SELECT MAX(fetch_date) FROM weather_readings
        )
        ORDER BY o.id, w.fetch_datetime DESC, observation_score DESC
    """)

    if _df.empty:
        return _df

    # The SQL observation_score is the WEATHER component only. Replace
    # the headline observation_score/condition with a genuine
    # observing-quality index that blends weather with the physics GOWC
    # already computes (seeing, jet stream, precipitation gate).
    from atmospheric import (calculate_seeing, calculate_jet_stream_impact,
                             observing_quality_score, observing_condition)

    _df = _df.rename(columns={"observation_score": "weather_score"})

    def _quality_row(r):
        seeing = calculate_seeing(
            r.get("temperature_c"), r.get("wind_speed_ms"),
            r.get("humidity_pct"), r.get("altitude_m", 0))
        _, jet_impact = calculate_jet_stream_impact(
            r.get("jet_stream_ms"), r.get("latitude", 0))
        return observing_quality_score(
            r.get("cloud_cover_pct"), r.get("humidity_pct"),
            r.get("wind_speed_ms"), r.get("precipitation_mm"),
            seeing, jet_impact)

    _df["observation_score"] = _df.apply(_quality_row, axis=1)
    _df["condition"] = _df["observation_score"].apply(observing_condition)
    return _df.sort_values("observation_score", ascending=False)

@st.cache_data(ttl=3600, show_spinner=False)
def load_windows():
    data = get_all_precomputed().get(
        "windows", pd.DataFrame())
    if not data.empty:
        return data
    data = load_precomputed("observing_windows_slim")
    if not data.empty:
        return data
    return load_precomputed("observing_windows")

@st.cache_data(ttl=3600, show_spinner=False)
def load_peak_times_cached(object_name=None, object_magnitude=None,
                           filter_band="V", wavelength_nm=550.0,
                           bandwidth_nm=100.0):
    if object_name:
        from peak_time import get_all_peak_times
        return get_all_peak_times(
            object_name, object_magnitude=object_magnitude,
            filter_band=filter_band, wavelength_nm=wavelength_nm,
            bandwidth_nm=bandwidth_nm)
    data = get_all_precomputed().get(
        "peak_times", pd.DataFrame())
    if not data.empty:
        return data
    return load_precomputed("peak_times")

@st.cache_data(ttl=3600, show_spinner=False)
def load_atmospheric_cached():
    data = get_all_precomputed().get(
        "atmospheric", pd.DataFrame())
    if not data.empty:
        return data
    return load_precomputed("atmospheric")

@st.cache_data(ttl=3600, show_spinner=False)
def load_efficiency_cached(telescope_type="optical"):
    if telescope_type == "optical":
        data = get_all_precomputed().get(
            "efficiency", pd.DataFrame())
        if not data.empty:
            return data
    return load_precomputed(f"efficiency_{telescope_type}")

def score_color(score):
    if score >= 80:   return "#1D9E75"
    elif score >= 60: return "#378ADD"
    elif score >= 40: return "#EF9F27"
    else:             return "#E24B4A"

def condition_emoji(condition):
    return {"Excellent": "🟢", "Good": "🔵",
            "Marginal": "🟡", "Poor": "🔴"}.get(condition, "⚪")

# ── Cached wrappers for heavy per-page computations ──────────────
@st.cache_data(ttl=3600, show_spinner=False)
def cached_reliability_scores(days):
    key = f"reliability_{days}d"
    pre = load_precomputed(key)
    if not pre.empty:
        return pre
    return calculate_reliability_scores(days=days)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_compare_sites(sites_tuple, days):
    return compare_sites(list(sites_tuple), days)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_calendar_data(obs, year, start_month, months):
    return build_calendar_data(obs, year, start_month, months)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_best_months(obs, year, months):
    return get_best_months(obs, year, months)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_snr_all(object_name, object_mag, exposure_s, moon_phase, moon_alt):
    return get_snr_for_all_observatories(
        object_name=object_name,
        object_magnitude=object_mag,
        exposure_time_s=exposure_s,
        observatories_df=load_data(),
        moon_phase_pct=moon_phase,
        moon_altitude_deg=moon_alt,
        seeing_data=load_atmospheric(),
        pwv_data=load_atmospheric()
    )

@st.cache_data(ttl=600, show_spinner=False)
def cached_forecast(lat, lon, days=7):
    from forecast import fetch_forecast as _ff, get_daily_summary as _gds
    fc = _ff(lat, lon, days=days)
    return fc, _gds(fc)

@st.cache_data(ttl=1800, show_spinner=False)
def cached_comets():
    return get_current_comets()

@st.cache_data(ttl=3600, show_spinner=False)
def cached_showers():
    pre = load_precomputed_raw("meteor_showers")
    if pre:
        return pre.get("showers", []), pre.get("active", []), pre.get("upcoming", [])
    return get_all_showers_sorted(), get_active_showers(), get_upcoming_showers(30)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_eclipse_events():
    pre = load_precomputed_raw("eclipse_events")
    if pre:
        return pre
    return get_upcoming_events()

@st.cache_data(ttl=3600, show_spinner=False)
def cached_best_obs_for_eclipse(event_name, event_date):
    key = f"eclipse_best_{event_date}_{event_name.replace(' ', '_')}"
    pre = load_precomputed_raw(key)
    if pre:
        return pre
    return get_best_observatories_for_eclipse(
        {"name": event_name, "date": event_date}, load_data())

@st.cache_data(ttl=3600, show_spinner=False)
def cached_airmass_curve(obs_name, obj_name, lat, lon, alt):
    return get_object_airmass_curve(obj_name, lat, lon, alt)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_compare_airmass(objects, lat, lon, alt):
    return compare_objects_airmass(list(objects), lat, lon, alt)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_reviews(obs_name):
    return get_reviews(obs_name), get_observatory_stats(obs_name)

@st.cache_data(ttl=600, show_spinner=False)
def cached_top_reviews():
    return get_top_rated_observatories(), get_recent_reviews(10)

df  = load_data()
win = load_windows()
peak = load_peak_times_cached()

# Real last-update timestamp, formatted once and reused everywhere.
def _format_last_updated(dataframe):
    if dataframe.empty or "fetch_datetime" not in dataframe.columns:
        return "No data yet"
    ts = dataframe["fetch_datetime"].iloc[0]
    try:
        return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(ts)

LAST_UPDATED = _format_last_updated(df)

st.caption(
    f"Last updated: {LAST_UPDATED} "
    f"· {len(df)} observatories monitored "
    f"· {len(OBJECTS)} astronomical objects"
)

# ── Sidebar navigation ────────────────────────────────
st.sidebar.image("assets/gowc_banner.png", width=220)
st.sidebar.markdown(f"<p style='font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:{TEXT2};padding:4px 12px 2px;margin:0'>Navigation</p>", unsafe_allow_html=True)

# Group pages into categories for a two-level sidebar nav.
# The page names inside must match the keys used by every
# downstream `if selected_page == ...` block.
PAGE_CATEGORIES = {
    "Overview": [
        "Home",
        "Live Weather Map",
    ],
    "Planning": [
        "Observing Windows",
        "Object Visibility",
        "Observing Proposal Planner",
    ],
    "Analysis": [
        "Atmospheric Analysis",
        "Historical Reliability",
        "Site Comparison",
        "Telescope Efficiency",
        "SNR Calculator",
        "Observatory Detail",
    ],
    "Sky Events": [
        "Sky Events",
    ],
    "More": [
        "Learn Astronomy",
        "Alert Subscriptions",
        "Observatory Reviews",
        "Feedback & Suggestions",
    ],
}

# Single dropdown listing every page, with non-selectable
# category headers as visual separators so all 24 pages are
# visible in one place.
_nav_options = []
_nav_headers = set()
for _cat, _pages in PAGE_CATEGORIES.items():
    _header = f"— {_cat} —"
    _nav_options.append(_header)
    _nav_headers.add(_header)
    _nav_options.extend(_pages)

_picked = st.sidebar.selectbox(
    "Navigation",
    _nav_options,
    index=_nav_options.index("Home"),
    label_visibility="collapsed",
    key="nav_page",
)

# If a category header was somehow selected, fall back to its
# first real page.
if _picked in _nav_headers:
    _cat_name = _picked.strip("— ").strip()
    selected_page = PAGE_CATEGORIES.get(_cat_name, ["Home"])[0]
else:
    selected_page = _picked

# Dynamic browser-tab title per page ("Live Weather Map · GOWC").
_tab_title = ("GOWC · Observatory Weather"
              if selected_page == "Home"
              else f"{selected_page} · GOWC")
components.html(
    f"<script>document.title = {json.dumps(_tab_title)};</script>",
    height=0,
)

# Current weather summary in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("**Live conditions**")
if not df.empty:
    best = df.iloc[0]
    st.sidebar.metric(
        "Best site tonight",
        best["observatory"].replace(
            " Observatory", "")[:20],
        f"{best['observation_score']}/100"
    )
    st.sidebar.metric(
        "Observatories monitored",
        len(df)
    )
    st.sidebar.caption(
        f"Updated: {df['fetch_datetime'].iloc[0]}"
    )

# Manual fetch is an admin action (it re-fetches the whole global
# dataset on our infra), so it's hidden from public visitors. Append
# ?admin=1 to the URL to reveal it. Scheduled GitHub Actions keep the
# data fresh for everyone automatically.
_is_admin = st.query_params.get("admin") == "1"

if _is_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Fetch Live Data** (admin)")

if _is_admin and st.sidebar.button("Fetch Live Data", use_container_width=True):
    with st.sidebar:
        with st.spinner("Fetching weather for all observatories..."):
            try:
                from fetch_weather import fetch_all_parallel, load_observatories
                from load_database import (build_coord_cache,
                                           upsert_weather_readings,
                                           insert_weather_history,
                                           utcnow)
                import json, os

                observatories = load_observatories()
                if observatories:
                    results, failed = fetch_all_parallel(
                        observatories, max_workers=12)

                    os.makedirs("data/bronze", exist_ok=True)
                    date_str = utcnow().strftime("%Y-%m-%d")
                    filename = f"data/bronze/raw_weather_{date_str}.json"
                    with open(filename, "w") as fp:
                        json.dump(results, fp, indent=2)

                    now = utcnow()
                    build_coord_cache()
                    upsert_weather_readings(results, now)
                    insert_weather_history(results, now)

                    load_data.clear()
                    fetched_at = now.strftime("%Y-%m-%d %H:%M UTC")
                    st.success(
                        f"Fetched {len(results)} observatories\n\n"
                        f"Last fetched: {fetched_at}"
                    )

                    with st.spinner("Precomputing dashboard data..."):
                        try:
                            from precompute import precompute_all
                            precompute_all()
                            get_all_precomputed.clear()
                            st.success("Dashboard data precomputed.")
                        except Exception as e:
                            st.warning(f"Precompute skipped: {e}")
                else:
                    st.error("No observatories found.")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Global Observatory Weather Tracker · "
    "Built by Ahzam Ahmed"
)

# ── Global empty-data guard ───────────────────────────
# If the core weather dataset failed to load (DB unreachable
# or no data yet), show a friendly message instead of letting
# every page crash on df.iloc[0].
if df.empty:
    st.warning(
        "Live weather data is currently unavailable. This can happen "
        "if the data source is being refreshed or temporarily "
        "unreachable. Please try again in a few minutes.",
        icon="⚠️",
    )
    st.caption(
        "If you are the site owner, use **Fetch Live Data** in the "
        "sidebar to repopulate the dataset."
    )
    st.stop()

# ═══════════════════════════════════════════════════════
# HOME — Landing page
# ═══════════════════════════════════════════════════════
if selected_page == "Home":
    st.image("assets/gowc_banner_cropped.png", use_container_width=True)

    _n_excellent  = len(df[df["condition"] == "Excellent"])
    _n_good       = len(df[df["condition"] == "Good"])
    _avg_score    = round(df["observation_score"].mean(), 1)
    _best_site    = df.iloc[0]["observatory"]
    _best_country = df.iloc[0]["country"]

    # ── Tagline + description ──────────────────────────
    st.markdown("""
<div style="text-align:center;padding:28px 20px 8px;">
  <div style="font-size:1.15rem;color:#7dafc8;letter-spacing:0.06em;text-transform:uppercase;font-weight:600;margin-bottom:10px;">
    Real-time weather intelligence for astronomers worldwide
  </div>
  <div style="font-size:1rem;color:#a8bfd4;max-width:780px;margin:0 auto;line-height:1.7;">
    GOWC monitors <strong style="color:#00d4ff;">1,163 professional observatories</strong> across the globe,
    delivering live weather conditions, atmospheric quality scores, and multi-day forecasts —
    so you always know where and when the sky is clearest.
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Live stat cards ────────────────────────────────
    st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0;">
  <div style="background:linear-gradient(135deg,#0d1b2a,#0f2236);border:1px solid #1e3a5f;border-top:3px solid #00d4ff;border-radius:10px;padding:18px 20px;text-align:center;">
    <div style="font-size:2rem;font-weight:800;color:#00d4ff;">{len(df):,}</div>
    <div style="font-size:0.72rem;color:#7dafc8;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Observatories Monitored</div>
  </div>
  <div style="background:linear-gradient(135deg,#0d1b2a,#0f2236);border:1px solid #1e3a5f;border-top:3px solid #1D9E75;border-radius:10px;padding:18px 20px;text-align:center;">
    <div style="font-size:2rem;font-weight:800;color:#1D9E75;">{_n_excellent:,}</div>
    <div style="font-size:0.72rem;color:#7dafc8;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Excellent Tonight</div>
  </div>
  <div style="background:linear-gradient(135deg,#0d1b2a,#0f2236);border:1px solid #1e3a5f;border-top:3px solid #378ADD;border-radius:10px;padding:18px 20px;text-align:center;">
    <div style="font-size:2rem;font-weight:800;color:#378ADD;">{_n_good:,}</div>
    <div style="font-size:0.72rem;color:#7dafc8;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Good Conditions</div>
  </div>
  <div style="background:linear-gradient(135deg,#0d1b2a,#0f2236);border:1px solid #1e3a5f;border-top:3px solid #EF9F27;border-radius:10px;padding:18px 20px;text-align:center;">
    <div style="font-size:2rem;font-weight:800;color:#EF9F27;">{_avg_score}</div>
    <div style="font-size:0.72rem;color:#7dafc8;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Global Avg Score</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Best site banner ───────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(90deg,#0d2137,#0a2e1f);border:1px solid #1D9E75;border-radius:10px;
            padding:14px 22px;display:flex;align-items:center;gap:16px;margin-bottom:28px;">
  <div style="font-size:1.6rem;">🏆</div>
  <div>
    <div style="font-size:0.7rem;color:#5dcaa5;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Best Site Tonight</div>
    <div style="font-size:1.1rem;font-weight:700;color:#e8f4fd;">{_best_site}</div>
    <div style="font-size:0.78rem;color:#7dafc8;">{_best_country}</div>
  </div>
  <div style="margin-left:auto;text-align:right;">
    <div style="font-size:1.8rem;font-weight:800;color:#1D9E75;">{int(df.iloc[0]['observation_score'])}<span style="font-size:1rem;color:#5dcaa5;">/100</span></div>
    <div style="font-size:0.7rem;color:#5dcaa5;">Observation Score</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Feature grid ───────────────────────────────────
    st.markdown("<div style='font-size:1.2rem;font-weight:700;color:#e8f4fd;margin-bottom:16px;'>Platform Features</div>", unsafe_allow_html=True)

    _features = [
        ("🗺️", "#00d4ff", "Live Weather Map",      "Real-time observation quality scores on an interactive world map with satellite imagery."),
        ("🔭", "#1D9E75", "Observing Windows",      "Best time windows and the peak observing hour tonight, factoring weather, darkness and moon."),
        ("🌌", "#9b59b6", "Object Visibility",      "See which galaxies, nebulae and planets are visible tonight at any chosen site."),
        ("🌬️", "#00b4d8", "Atmospheric Analysis",  "Seeing quality, precipitable water vapour, jet stream impact and turbulence indices."),
        ("📈", "#1D9E75", "Historical Reliability", "Long-term reliability scores, trend direction and percentage of excellent nights."),
        ("🔬", "#EF9F27", "Site Comparison",        "Compare up to 5 observatories side-by-side across all weather and atmospheric metrics."),
        ("📝", "#e74c3c", "Observing Proposal Planner", "Build a real observing proposal: targets, time, moon, SNR-solved exposures, and a best-months calendar."),
        ("🛰️", "#378ADD", "Telescope Efficiency",  "Efficiency ratings for optical, infrared and radio telescopes based on live conditions."),
        ("🌠", "#00d4ff", "Sky Events",             "Comets, asteroids, satellite passes, meteor showers and eclipses — with the best sites to view them."),
    ]

    _feat_html = "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px;'>"
    for icon, color, title, desc in _features:
        _feat_html += f"""
<div style="background:#0d1b2a;border:1px solid #1e2d40;border-radius:10px;padding:16px 18px;display:flex;gap:14px;align-items:flex-start;">
  <div style="background:{color}22;border-radius:8px;padding:8px;font-size:1.3rem;flex-shrink:0;">{icon}</div>
  <div>
    <div style="font-size:0.9rem;font-weight:700;color:#e8f4fd;margin-bottom:4px;">{title}</div>
    <div style="font-size:0.78rem;color:#7dafc8;line-height:1.5;">{desc}</div>
  </div>
</div>"""
    _feat_html += "</div>"
    st.markdown(_feat_html, unsafe_allow_html=True)

    # ── Quick start ────────────────────────────────────
    st.markdown("<div style='font-size:1.2rem;font-weight:700;color:#e8f4fd;margin-bottom:16px;'>Getting Started</div>", unsafe_allow_html=True)

    _steps = [
        ("01", "#00d4ff", "Open Live Weather Map",    "Click 'Live Weather Map' in the sidebar to see tonight's conditions for all 1,163 observatories on the globe."),
        ("02", "#1D9E75", "Search or Browse",         "Use the search bar to filter by observatory name or country, or zoom into any region on the map."),
        ("03", "#378ADD", "Explore Observatory Detail","Click any marker or ranking entry to open a detailed page with mini-map, nearby sites, and history."),
        ("04", "#EF9F27", "Refresh Live Data",        "Hit 'Fetch Live Data' in the sidebar to pull fresh weather readings from all observatories on demand."),
        ("05", "#9b59b6", "Plan & Compare",           "Use the Observing Proposal Planner, Site Comparison, and Atmospheric Analysis to make informed observing decisions."),
    ]

    _steps_html = "<div style='display:flex;flex-direction:column;gap:10px;margin-bottom:28px;'>"
    for num, color, title, desc in _steps:
        _steps_html += f"""
<div style="background:#0d1b2a;border:1px solid #1e2d40;border-left:3px solid {color};border-radius:10px;padding:14px 18px;display:flex;gap:16px;align-items:flex-start;">
  <div style="font-size:1.1rem;font-weight:800;color:{color};flex-shrink:0;min-width:28px;">{num}</div>
  <div>
    <div style="font-size:0.9rem;font-weight:700;color:#e8f4fd;margin-bottom:3px;">{title}</div>
    <div style="font-size:0.78rem;color:#7dafc8;line-height:1.5;">{desc}</div>
  </div>
</div>"""
    _steps_html += "</div>"
    st.markdown(_steps_html, unsafe_allow_html=True)

    # ── Footer info ────────────────────────────────────
    st.markdown(f"""
<div style="background:#0a1628;border:1px solid #1e2d40;border-radius:8px;padding:12px 18px;
            font-size:0.78rem;color:#5c7a96;text-align:center;">
  ℹ️ &nbsp; Data last updated: <strong style="color:#7dafc8;">{LAST_UPDATED}</strong>
  &nbsp;·&nbsp; {len(df):,} observatories monitored
  &nbsp;·&nbsp; {len(OBJECTS)} astronomical objects tracked
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# METHODOLOGY — appended to Home inside an expander
# ═══════════════════════════════════════════════════════
if selected_page == "Home":
  with st.expander("📖 Methodology & physics — how the numbers are calculated"):
    st.markdown("""
GOWC combines live weather data with established astronomy physics to estimate how
good observing conditions are at each site — right now, tonight, and over the coming
week.
""")

    st.info(
        "GOWC provides forecasts and physics-based **estimates** for observation "
        "planning. It is not a substitute for on-site measurements or official "
        "observatory conditions.",
        icon="⚠️"
    )

    st.subheader("Observing-Quality Index")
    st.markdown(r"""
Each observatory's headline **0–100 score** is a *multiplicative* observing-quality
index — the same approach used by ClearDarkSky and Meteoblue astronomy indices. Each
factor is a 0–1 fraction and they multiply, so a single show-stopper (thick cloud,
rain, terrible seeing) correctly drags the whole night down regardless of the rest:

$$Q = \text{clarity}\times\text{dryness}\times\text{wind}\times\text{seeing}\times\text{jet}\times\text{precip gate}$$

| Factor | Behaviour |
|---|---|
| **Clarity** | $(1-\text{cloud})^{1.5}$ — non-linear; even light cloud bites |
| **Dryness** | 1.0 below 70% RH, falling toward 0.5 near saturation |
| **Wind stability** | 1.0 below ~8 m/s, degrading toward 0.2 in gales |
| **Seeing** | 1.0 at ≤0.7″, falling to ~0.25 by ~3″ (Fried-based) |
| **Jet stream** | 1.0 (negligible) down to 0.5 (severe turbulence aloft) |
| **Precip gate** | any measurable rain ⇒ ×0.05 (dome closed) |

| Score | Condition |
|---|---|
| 80–100 | Excellent |
| 60–79 | Good |
| 40–59 | Marginal |
| 0–39 | Poor |

Because the index is harsh by design, most sites score modestly most of the time —
which is realistic. A simpler weather-only score is kept internally as `weather_score`.
""")

    st.subheader("Airmass")
    st.markdown(r"""
Airmass measures how much atmosphere light passes through (1.0 at the zenith,
rising toward the horizon). GOWC uses the **Pickering (2002)** formula, which is
accurate near the horizon where the simple plane-parallel $\sec(z)$ approximation
breaks down:

$$X = \frac{1}{\sin\!\left(h + \dfrac{244}{165 + 47\,h^{1.1}}\right)}$$

where $h$ is the apparent altitude in degrees.
""")

    st.subheader("Astronomical Seeing")
    st.markdown(r"""
Seeing — the blurring of point sources by atmospheric turbulence — is computed from
the **Fried parameter** $r_0$, not a heuristic. The turbulence strength $\int C_n^2\,dh$
is modelled with a Hufnagel–Valley-style decomposition into a free-atmosphere term
(driven by upper-level wind) and a boundary-layer term (driven by ground wind shear
and humidity, suppressed at high sites that sit above the surface layer). Then:

$$r_0 = \left(0.423\,k^2\,X \int C_n^2\,dh\right)^{-3/5} \qquad \theta_{\mathrm{FWHM}} = 0.98\,\lambda / r_0$$

where $k = 2\pi/\lambda$ and $X$ is the airmass. The model is calibrated so the best
sites reproduce their published median seeing — for example a high, dry 4200 m peak
yields $r_0 \approx 20$ cm (seeing ≈ 0.5″), a 2600 m site ≈ 0.8″, and a 2300 m site
≈ 0.9″ — with each observatory's value driven by its own altitude and live weather.
""")

    st.subheader("Atmospheric Extinction")
    st.markdown(r"""
Light is dimmed by the atmosphere by an amount that grows with airmass and depends
on the observing band and the **site's altitude** — higher, drier sites sit above
more of the atmosphere, so they lose less light. GOWC gives **every observatory its
own per-filter extinction coefficient $k$**, scaling it by the site's elevation with
an exponential atmospheric-column model (scale height ≈ 8 km). The reference
coefficients are calibrated against published professional-site measurements, so a
high dry peak transmits noticeably more than a low coastal site at the same airmass.

The atmospheric transmission is then:

$$T = 10^{-k\,X/2.5}$$

where $k$ is the site/band extinction coefficient and $X$ the airmass.
""")

    st.subheader("Signal-to-Noise (SNR)")
    st.markdown(r"""
The SNR Calculator uses the standard **CCD equation**, including a scintillation
term and surface-brightness handling for extended objects:

$$\mathrm{SNR} = \frac{N_{\star}}{\sqrt{N_{\star} + N_{\mathrm{sky}} + N_{\mathrm{dark}} + N_{\mathrm{read}}^2 + N_{\mathrm{scint}}^2}}$$

where $N_\star$ is source counts, $N_{\mathrm{sky}}$ sky-background counts,
$N_{\mathrm{dark}}$ dark current, $N_{\mathrm{read}}$ read noise, and
$N_{\mathrm{scint}}$ scintillation noise.

The same SNR and airmass/extinction physics feed several pages: **Object Visibility**
ranks sites by atmospheric transmission $10^{-kX/2.5}$, **Peak Observing Time** picks
the hour of maximum SNR for a target, and the **Observing Proposal Planner** solves the
exposure time needed to reach a target SNR (organised around a professional 11-section
proposal).
""")

    st.subheader("Data Sources & References")
    st.markdown("""
- **Weather** — [Open-Meteo](https://open-meteo.com) (free, open-source API)
- **Ephemerides** — [PyEphem](https://rhodesmill.org/pyephem/)
- **Airmass** — Pickering, K. A. (2002), *The Southern Limits of the Ancient Star Catalog*
- **Extinction** — King (1985); ESO Paranal site monitoring; ORM La Palma
- **SFR / Hα methodology** — Kennicutt (1998)
""")

    st.markdown("---")
    st.caption(f"Data last updated: {LAST_UPDATED} · {len(df):,} observatories · {len(OBJECTS)} objects · Built by Ahzam Ahmed")


# ═══════════════════════════════════════════════════════
# TAB 1 — Live Weather Map
# ═══════════════════════════════════════════════════════
if selected_page == "Live Weather Map":
    # ── Banner + compact stats row ─────────────────────────
    _best_name = df.iloc[0]["observatory"].replace(" Observatory","").replace(" Telescope","")
    _n_excellent = len(df[df["condition"] == "Excellent"])
    _avg_score = round(df["observation_score"].mean(), 1)

    st.image("assets/gowc_banner_cropped.png", use_container_width=True)

    _hc1, _hc2, _hc3, _hc4 = st.columns(4)
    _hc1.metric("Total Sites", f"{len(df):,}")
    _hc2.metric("Excellent Tonight", f"{_n_excellent:,}")
    _hc3.metric("Avg Score", f"{_avg_score} / 100")
    _hc4.metric("Best Tonight", _best_name[:28])

    st.subheader("World map — live observation quality")

    _map_col1, _map_col2 = st.columns([3, 1])
    with _map_col1:
        _obs_search = st.text_input("Search observatory", placeholder="e.g. Mauna Kea, Chile, Spain...", label_visibility="collapsed", key="map_obs_search")
    with _map_col2:
        _map_style = st.radio("Map style", ["Streets", "Satellite"], horizontal=True, index=0, key="main_map_style")

    if _obs_search:
        _q = _obs_search.lower()
        _df_map = df[df["observatory"].str.lower().str.contains(_q) | df["country"].str.lower().str.contains(_q)].copy()
        if _df_map.empty:
            st.warning(f"No observatories found matching '{_obs_search}'.")
        else:
            st.caption(f"{len(_df_map)} result(s) for '{_obs_search}'")
    else:
        _df_map = df.copy()

    import plotly.graph_objects as go
    import numpy as np

    _color_map = {"Excellent": "#1D9E75", "Good": "#00b4d8",
                  "Marginal": "#EF9F27", "Poor": "#E24B4A"}

    # Cluster toggle — off when searching (already filtered)
    _cluster_on = st.checkbox("Cluster markers", value=not bool(_obs_search), key="map_cluster")

    _map_fig = go.Figure()

    if _cluster_on and len(_df_map) > 20:
        # Grid-bin markers: cell size ~15° at world view
        _grid = 15.0
        _df_map["_clat"] = (_df_map["latitude"]  // _grid) * _grid + _grid / 2
        _df_map["_clon"] = (_df_map["longitude"] // _grid) * _grid + _grid / 2
        _cond_order = ["Excellent", "Good", "Marginal", "Poor"]

        for (_clat, _clon), _grp in _df_map.groupby(["_clat", "_clon"]):
            _n      = len(_grp)
            _avg    = _grp["observation_score"].mean()
            # dominant condition = most common
            _dom    = _grp["condition"].value_counts().idxmax()
            _cc     = _color_map.get(_dom, "#888")
            _size   = min(18 + _n * 0.35, 52)
            _names  = _grp["observatory"].tolist()
            _preview = "<br>".join(_names[:5]) + (f"<br>…+{_n-5} more" if _n > 5 else "")
            _map_fig.add_trace(go.Scattermapbox(
                lat=[_clat], lon=[_clon],
                mode="markers+text",
                marker=dict(size=_size, color=_cc, opacity=0.85),
                text=[str(_n)],
                textfont=dict(color="white", size=11),
                hovertemplate=(
                    f"<b>{_n} observatories</b><br>"
                    f"Avg score: {_avg:.0f}/100<br>"
                    f"Best condition: {_dom}<br>"
                    f"{_preview}<extra></extra>"
                ),
                showlegend=False,
            ))

        # Legend as a separate dummy trace per condition present
        for _cond in _cond_order:
            if _cond in _df_map["condition"].values:
                _map_fig.add_trace(go.Scattermapbox(
                    lat=[None], lon=[None], mode="markers",
                    marker=dict(size=10, color=_color_map[_cond]),
                    name=_cond, showlegend=True,
                ))
    else:
        _size_map = {"Excellent": 10, "Good": 8, "Marginal": 7, "Poor": 6}
        for condition, grp in _df_map.groupby("condition"):
            _c = _color_map.get(condition, "#888888")
            _s = _size_map.get(condition, 7)
            _map_fig.add_trace(go.Scattermapbox(
                lat=grp["latitude"],
                lon=grp["longitude"],
                mode="markers",
                marker=dict(size=_s, color=_c, opacity=0.9),
                text=grp.apply(lambda r: (
                    f"<b>{r['observatory']}</b><br>"
                    f"{r['country']} · {r['altitude_m']}m<br>"
                    f"Score: <b>{int(r['observation_score'])}/100</b> [{r['condition']}]<br>"
                    f"Cloud: {r['cloud_cover_pct']}% · Humidity: {r['humidity_pct']}%<br>"
                    f"Wind: {r['wind_speed_ms']} m/s · Temp: {r['temperature_c']}°C"
                ), axis=1),
                hovertemplate="%{text}<extra></extra>",
                name=condition,
            ))

    if _obs_search and not _df_map.empty:
        _map_clat = _df_map["latitude"].mean()
        _map_clon = _df_map["longitude"].mean()
        _map_zoom = 3 if len(_df_map) > 5 else 5
    else:
        _map_clat, _map_clon, _map_zoom = 20, 0, 1.4

    if _map_style == "Satellite":
        _mapbox_cfg = dict(
            style="white-bg",
            layers=[dict(
                sourcetype="raster",
                source=["https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}"],
                below="traces",
            )],
            center=dict(lat=_map_clat, lon=_map_clon),
            zoom=_map_zoom,
        )
    else:
        _mapbox_cfg = dict(
            style="open-street-map",
            center=dict(lat=_map_clat, lon=_map_clon),
            zoom=_map_zoom,
        )

    _map_fig.update_layout(
        mapbox=_mapbox_cfg,
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=0.01,
            xanchor="left",   x=0.01,
            bgcolor="rgba(10,10,20,0.7)",
            bordercolor="#1e2d40",
            borderwidth=1,
            font=dict(color="#cdd9e5", size=12),
        ),
        uirevision="map",
    )
    st.plotly_chart(_map_fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
        "displaylogo": False,
    })

    st.markdown("---")
    st.subheader("Tonight's Best Observatories")
    _top10 = df.nlargest(10, "observation_score").reset_index(drop=True)
    _medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    _top10_cols = st.columns(5)
    for i, r in _top10.iterrows():
        _col = _top10_cols[i % 5]
        _score = int(r["observation_score"])
        _medal = _medals.get(i, f"#{i+1}")
        _cond_icon = {"Excellent": "🟢", "Good": "🔵", "Marginal": "🟡", "Poor": "🔴"}.get(r["condition"], "⚪")
        with _col:
            st.metric(
                label=f"{_medal} {r['observatory'][:22]}",
                value=f"{_score}/100",
                delta=r["condition"],
            )
            st.progress(_score / 100)
            st.caption(f"{r['country']} · {int(r['altitude_m'])}m · Cloud {r['cloud_cover_pct']}%")

    st.markdown("---")
    with st.expander("Observation quality rankings", expanded=False):
        col_left, col_right = st.columns([2, 1])
        with col_left:
            for _, row in df.iterrows():
                emoji = condition_emoji(row["condition"])
                st.markdown(
                    f"{emoji} **{row['observatory']}** "
                    f"— {row['country']}")
                st.progress(
                    int(row["observation_score"]) / 100,
                    text=f"{row['observation_score']}/100 · "
                         f"Cloud {row['cloud_cover_pct']}% · "
                         f"Humidity {row['humidity_pct']}% · "
                         f"Wind {row['wind_speed_ms']} m/s"
                )
        with col_right:
            st.dataframe(
                df[["observatory", "observation_score",
                    "condition"]].rename(columns={
                    "observatory":       "Observatory",
                    "observation_score": "Score",
                    "condition":         "Condition"
                }),
                hide_index=True,
                height=700
            )

    st.markdown("---")
    st.subheader("📥 Export for Google Maps / Google Earth")
    st.caption(
        "Download your observatory data to view in "
        "Google Maps or Google Earth with live scores."
    )

    from export_kml import generate_kml, generate_csv_for_maps

    ex1, ex2 = st.columns(2)

    with ex1:
        kml_data = generate_kml(df)
        st.download_button(
            label="🌍 Download KML for Google Earth",
            data=kml_data,
            file_name=f"observatories_{utcnow().strftime('%Y-%m-%d')}.kml",
            mime="application/vnd.google-earth.kml+xml",
            help="Open this file in Google Earth to see all observatories with live scores"
        )
        st.caption(
            "Opens in Google Earth desktop or web. "
            "Shows all observatories colour-coded by "
            "observation quality."
        )

    with ex2:
        csv_data = generate_csv_for_maps(df)
        st.download_button(
            label="🗺️ Download CSV for Google My Maps",
            data=csv_data,
            file_name=f"observatories_maps_{utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            help="Import to maps.google.com/maps/d to create your own custom map"
        )
        st.caption(
            "Go to maps.google.com/maps/d → Create → Import. "
            "Creates a custom Google Map with all 1275 observatories."
        )

    st.info(
        "💡 **Google My Maps tip:** After importing the CSV, "
        "click 'Style by data column' → select 'Condition' "
        "to colour-code markers by Excellent/Good/Marginal/Poor."
    )

# ═══════════════════════════════════════════════════════
# TAB 2 — Observing Windows
# ═══════════════════════════════════════════════════════
if selected_page == "Observing Windows":
    page_header("🌙", "Tonight's Observing Windows",
        "Dark-time windows plus the peak observing hour for every site. "
        "Scores adjusted for moon phase and position; dark hours from "
        "astronomical twilight (-18°).")

    if not win.empty:
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Moon Phase",        win.iloc[0]["moon_phase"])
        w2.metric("Moon Illumination",
                  f"{win.iloc[0]['moon_phase_pct']}%")
        w3.metric("Best Site Tonight",
                  win.iloc[0]["observatory"].replace(
                      " Observatory", ""))
        w4.metric("Best Score (moon-adjusted)",
                  f"{win.iloc[0]['final_score']} / 100")

        st.markdown("---")
        st.subheader("Top 10 sites for tonight")
        for _, row in win.head(10).iterrows():
            emoji = condition_emoji(row["quality"])
            with st.expander(
                f"{emoji} {row['observatory']} — "
                f"{row['final_score']}/100 [{row['quality']}] · "
                f"{row['dark_start']} → {row['dark_end']} "
                f"({row['dark_hours']}h dark)"
            ):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Weather Score",
                          f"{row['weather_score']}/100")
                d2.metric("Moon Penalty",
                          f"-{row['moon_penalty']}")
                d3.metric("Final Score",
                          f"{row['final_score']}/100")
                d4.metric("Dark Hours",
                          f"{row['dark_hours']}h")
                m1, m2, m3 = st.columns(3)
                m1.metric("Moon Phase", row["moon_phase"])
                m2.metric("Moon Rise",  row["moon_rise"])
                m3.metric("Moon Set",   row["moon_set"])

        st.markdown("---")
        st.subheader("All observatories — full window table")
        display_df = win[[
            "observatory", "country", "dark_start", "dark_end",
            "dark_hours", "moon_phase", "moon_phase_pct",
            "weather_score", "moon_penalty", "final_score", "quality"
        ]].rename(columns={
            "observatory":    "Observatory",
            "country":        "Country",
            "dark_start":     "Dark Start",
            "dark_end":       "Dark End",
            "dark_hours":     "Dark Hours",
            "moon_phase":     "Moon Phase",
            "moon_phase_pct": "Moon %",
            "weather_score":  "Weather Score",
            "moon_penalty":   "Moon Penalty",
            "final_score":    "Final Score",
            "quality":        "Quality"
        })
        st.dataframe(display_df, hide_index=True, height=600)
        st.download_button(
            label="Download tonight's window table as CSV",
            data=display_df.to_csv(index=False),
            file_name=f"observing_windows_"
                      f"{utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

# ═══════════════════════════════════════════════════════
# TAB 3 — Object Visibility
# ═══════════════════════════════════════════════════════
if selected_page == "Object Visibility":
    page_header("🔭", "Object Visibility",
        "Where and how well a target can be seen — site ranking, airmass "
        "curve, or a live sky chart.")
    _vis_sub = st.radio(
        "View", ["Site ranking", "Airmass curve", "Live sky chart"],
        horizontal=True, key="vis_sub", label_visibility="collapsed")
    st.markdown("---")
else:
    _vis_sub = None

if _vis_sub == "Site ranking":
    col_filter, col_select = st.columns([1, 2])
    with col_filter:
        obj_type = st.selectbox(
            "Filter by type",
            ["All", "Planets", "Dwarf Planets & Asteroids",
            "Galaxies", "Nebulae", "Star Clusters",
            "Famous Stars", "Special Objects",
            "Full Messier Catalogue", "NGC Objects",
            "Exoplanets"]
        )

    type_map = {
        "All":                       None,
        "Planets":                   "planet",
        "Dwarf Planets & Asteroids": ["dwarf_planet", "asteroid"],
        "Galaxies":                  "galaxy",
        "Nebulae":                   "nebula",
        "Star Clusters":             "cluster",
        "Famous Stars":              "star",
        "Special Objects":           "special",
        "Full Messier Catalogue":    "messier",
        "NGC Objects":               "ngc",
        "Exoplanets":                "exoplanet"
    }

    selected_type = type_map[obj_type]
    filtered_objects = {
        k: v for k, v in OBJECTS.items()
        if selected_type is None
        or (isinstance(selected_type, list)
           and v["type"] in selected_type)
        or (selected_type == "messier"
           and k.startswith("M") and "—" in k)
        or (selected_type == "ngc"
           and k.startswith("NGC"))
        or (isinstance(selected_type, str)
            and selected_type not in ["messier", "ngc"]
           and v["type"] == selected_type)
   }

    with col_select:
        selected_object = st.selectbox(
            "Select target object",
            list(filtered_objects.keys())
        )

    st.markdown("---")

    if selected_object:
        with st.spinner(
            f"Calculating visibility for {selected_object}..."
        ):
            best_obs = get_best_observatories_for_object(
                selected_object, df)

        if best_obs.empty:
            st.warning(
                f"{selected_object} is currently below the horizon "
                f"at all monitored observatories."
            )
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Observatories with view", len(best_obs))
            m2.metric("Best observatory",
                      best_obs.iloc[0]["observatory"].replace(
                          " Observatory", "").replace(
                          " Telescope", ""))
            m3.metric("Best altitude",
                      f"{best_obs.iloc[0]['altitude_deg']}°")
            m4.metric("Combined score",
                      f"{best_obs.iloc[0]['combined_score']} / 100")

            st.markdown("---")
            sample_vis = calculate_visibility(
                df.iloc[0]["latitude"],
                df.iloc[0]["longitude"],
                selected_object
            )
            obj_type_label = filtered_objects[
                selected_object]["type"].replace("_", " ").title()
            st.info(
                f"**{selected_object}** is a {obj_type_label}. "
                f"Currently visible from **{len(best_obs)}** of "
                f"{len(df)} monitored observatories. "
                f"Minimum altitude required: "
                f"{sample_vis['min_altitude']}° above horizon."
             )

# Show extra info for exoplanets
            if filtered_objects.get(selected_object, {}).get(
                    "type") == "exoplanet":
                from exoplanets import get_exoplanet_info
                exo_info = get_exoplanet_info(selected_object)
                if exo_info:
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Distance",
                             f"{exo_info['distance_ly']} ly")
                    e2.metric("Planet Type",
                             exo_info["type"])
                    e3.metric("Discovery Year",
                             exo_info["discovery_year"])
                    e4.metric("Discovery Method",
                             exo_info["method"])
                    st.info(
                       f"**{exo_info['name']}** orbits "
                       f"**{exo_info['host']}** at "
                       f"{exo_info['distance_ly']} light years. "
                       f"Discovered in {exo_info['discovery_year']} "
                       f"using {exo_info['method']}. "
                       f"{exo_info['notes']}."
                 )


            st.subheader(
                f"Best sites to observe {selected_object} tonight")
            for _, row in best_obs.head(10).iterrows():
                qual  = row["visibility_quality"]
                emoji = {"Excellent": "🟢", "Good": "🔵",
                         "Marginal": "🟡"}.get(qual, "⚪")
                with st.expander(
                    f"{emoji} {row['observatory']} — "
                    f"Combined {row['combined_score']}/100 · "
                    f"Altitude {row['altitude_deg']}° "
                    f"{row['direction']} · {qual}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Altitude",
                              f"{row['altitude_deg']}°")
                    _am = row.get("airmass")
                    c2.metric("Airmass",
                              f"{_am:.2f}" if _am else "—")
                    c3.metric("Extinction",
                              f"{row['extinction_mag']:.2f} mag"
                              if row.get("extinction_mag") is not None else "—")
                    c4.metric("Hours Visible",
                              f"{row['hours_visible']}h")
                    c5.metric("Combined Score",
                              f"{row['combined_score']}/100")
                    st.caption(
                        f"Rises: {row['rise_time']} · "
                        f"Sets: {row['set_time']} · "
                        f"Located in {row['country']}"
                    )

            st.markdown("---")
            st.subheader("All observatories with visibility")
            display = best_obs[[
                "observatory", "country", "altitude_deg",
                "airmass", "extinction_mag", "direction",
                "hours_visible", "rise_time",
                "set_time", "weather_score", "combined_score",
                "visibility_quality"
            ]].rename(columns={
                "observatory":        "Observatory",
                "country":            "Country",
                "altitude_deg":       "Altitude (°)",
                "airmass":            "Airmass",
                "extinction_mag":     "Extinction (mag)",
                "direction":          "Direction",
                "hours_visible":      "Hours Visible",
                "rise_time":          "Rises",
                "set_time":           "Sets",
                "weather_score":      "Weather Score",
                "combined_score":     "Combined Score",
                "visibility_quality": "Quality"
            })
            st.dataframe(display, hide_index=True, height=500)
            st.download_button(
                label=f"Download visibility table for "
                      f"{selected_object}",
                data=display.to_csv(index=False),
                file_name=f"visibility_"
                          f"{selected_object.replace(' ', '_')}_"
                          f"{utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )

# ═══════════════════════════════════════════════════════
# Peak Observing Time — now a section within Observing Windows
# ═══════════════════════════════════════════════════════
if selected_page == "Observing Windows":
    st.markdown("---")
    st.subheader("⏰ Peak observing hour & hourly breakdown")
    st.caption(
        "The single best hour to observe tonight at each observatory. "
        "Toggle on a target object to factor in its altitude "
        "alongside weather, darkness, and moon position."
    )

    use_object           = st.toggle(
        "Factor in a specific target object", value=False)
    selected_peak_object = None

    if use_object:
        pk_col1, pk_col2 = st.columns([1, 2])
        with pk_col1:
            pk_type = st.selectbox(
                "Object type",
                ["All", "Planets", "Galaxies", "Nebulae",
                 "Star Clusters", "Famous Stars",
                 "Full Messier Catalogue", "NGC Objects"],
                key="peak_type"
            )
        pk_type_map = {
            "All":                    None,
            "Planets":                "planet",
            "Galaxies":               "galaxy",
            "Nebulae":                "nebula",
            "Star Clusters":          "cluster",
            "Famous Stars":           "star",
            "Full Messier Catalogue": "messier",
            "NGC Objects":            "ngc",
            "Exoplanets":             "exoplanet"
        }
        pk_selected_type = pk_type_map[pk_type]
        pk_filtered = {
            k: v for k, v in OBJECTS.items()
            if pk_selected_type is None
            or (pk_selected_type == "messier"
                and k.startswith("M") and "—" in k)
            or (pk_selected_type == "ngc"
                and k.startswith("NGC"))
            or (isinstance(pk_selected_type, str)
                and pk_selected_type not in ["messier", "ngc", "exoplanet"]
                and v["type"] == pk_selected_type)
        }
        with pk_col2:
            selected_peak_object = st.selectbox(
                "Select target object",
                list(pk_filtered.keys()),
                key="peak_object"
            )

        # Band + magnitude → drives a real hourly SNR calculation.
        pk_bcol1, pk_bcol2 = st.columns(2)
        with pk_bcol1:
            _pk_filter_name = st.selectbox(
                "Filter / band",
                list(PHOTOMETRIC_FILTERS.keys()),
                index=2, key="peak_filter",
                help="SNR is computed in this band; narrowband (Hα, "
                     "OIII) collects far fewer photons."
            )
        _pk_filt = PHOTOMETRIC_FILTERS[_pk_filter_name]
        with pk_bcol2:
            _pk_default_mag = float(OBJECT_MAGNITUDES.get(selected_peak_object, 8.0))
            _pk_mag = st.number_input(
                "Object magnitude", min_value=-5.0, max_value=25.0,
                value=_pk_default_mag, step=0.1, key="peak_mag",
                help="Catalog magnitude (editable). Drives SNR."
            )

    with st.spinner("Calculating peak observing times..."):
        if selected_peak_object:
            peak = load_peak_times_cached(
                object_name=selected_peak_object,
                object_magnitude=_pk_mag,
                filter_band=_pk_filt["band"],
                wavelength_nm=_pk_filt["wavelength_nm"],
                bandwidth_nm=_pk_filt["bandwidth_nm"],
            )
        else:
            peak = load_peak_times_cached()

    if selected_peak_object:
        st.success(
            f"Peak hour chosen by **signal-to-noise** for "
            f"**{selected_peak_object}** in the {_pk_filt['band']} band "
            f"(mag {_pk_mag}) — accounts for altitude, airmass "
            f"extinction, sky brightness and seeing."
        )

    if not peak.empty:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Best Observatory",
                  peak.iloc[0]["observatory"].replace(
                      " Observatory", "").replace(
                      " Telescope", ""))
        p2.metric("Peak Hour",    peak.iloc[0]["peak_hour"])
        _peak_snr = peak.iloc[0].get("peak_snr") if selected_peak_object else None
        if _peak_snr is not None:
            p3.metric("Peak SNR", f"{_peak_snr}")
        else:
            p3.metric("Peak Score",
                      f"{peak.iloc[0]['peak_score']} / 100")
        p4.metric("Good Hours Tonight",
                  f"{peak.iloc[0]['total_good_hours']}h")

        st.markdown("---")

        selected_obs = st.selectbox(
            "Select observatory to see hourly breakdown",
            peak["observatory"].tolist(),
            key="peak_selector"
        )

        selected_row = peak[
            peak["observatory"] == selected_obs].iloc[0]

        st.markdown(
            f"**{selected_obs}** — "
            f"Peak at {selected_row['peak_hour']} · "
            f"Best window: {selected_row['window_start']} → "
            f"{selected_row['window_end']} · "
            f"{selected_row['total_good_hours']} good hours"
        )

        if selected_peak_object and selected_row.get("peak_obj_alt"):
            st.info(
                f"**{selected_peak_object}** reaches "
                f"**{selected_row['peak_obj_alt']}°** altitude "
                f"at peak observing time."
            )

        st.markdown("---")

        # Hourly chart — Plotly
        import plotly.graph_objects as go
        hours    = [h["hour"] for h in selected_row["hourly_data"]]
        scores   = [h["combined_score"] for h in selected_row["hourly_data"]]
        obj_alts = [h.get("object_altitude") for h in selected_row["hourly_data"]]
        _pcolors = ["#1D9E75" if s>=80 else "#378ADD" if s>=60 else "#EF9F27" if s>=40 else "#E24B4A" if s>0 else "#30363d" for s in scores]
        _xlabels = [f"{h:02d}:00" for h in range(24)]
        _peak_idx = scores.index(max(scores))
        _pfig = go.Figure()
        _pfig.add_trace(go.Bar(x=_xlabels, y=scores, marker_color=_pcolors, name="Score", hovertemplate="%{x}<br>Score: %{y:.0f}/100<extra></extra>"))
        if selected_peak_object and any(a is not None for a in obj_alts):
            _scaled = [(a/90*100) if a is not None and a>0 else 0 for a in obj_alts]
            _pfig.add_trace(go.Scatter(x=_xlabels, y=_scaled, mode="lines", line=dict(color="#AFA9EC", width=2, dash="dash"), name="Object altitude (scaled)"))
        _pfig.add_annotation(x=_xlabels[_peak_idx], y=scores[_peak_idx]+8, text=f"Peak<br>{_xlabels[_peak_idx]}<br>{scores[_peak_idx]:.0f}/100", showarrow=False, font=dict(color="white", size=10, family="sans-serif"), bgcolor="rgba(29,158,117,0.3)", bordercolor="#1D9E75", borderwidth=1)
        _pfig.update_layout(
            title=f"Hourly Observing Score — {selected_obs}" + (f" — {selected_peak_object}" if selected_peak_object else "") + f" — {utcnow().strftime('%Y-%m-%d')} UTC",
            xaxis_title="Hour (UTC)", yaxis_title="Combined Score",
            yaxis=dict(range=[0, 115]),
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2,
            font=dict(color=TEXT, family="sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=380, margin=dict(l=40, r=20, t=60, b=60)
        )
        st.plotly_chart(_pfig, use_container_width=True)

        st.markdown("---")
        st.subheader("Hourly breakdown table")
        hourly = pd.DataFrame(selected_row["hourly_data"])
        cols   = ["hour", "sun_altitude", "moon_altitude",
                  "darkness_score", "moon_score",
                  "weather_score", "combined_score", "is_dark"]
        rename = {
            "hour":           "Hour (UTC)",
            "sun_altitude":   "Sun Alt (°)",
            "moon_altitude":  "Moon Alt (°)",
            "darkness_score": "Darkness",
            "moon_score":     "Moon Score",
            "weather_score":  "Weather",
            "combined_score": "Combined",
            "is_dark":        "Is Dark"
        }
        if selected_peak_object:
            cols.insert(4, "object_altitude")
            rename["object_altitude"] = "Object Alt (°)"
        st.dataframe(
            hourly[cols].rename(columns=rename),
            hide_index=True, height=400
        )

        st.markdown("---")
        st.subheader(
            "Top 10 observatories by peak score tonight")
        st.dataframe(
            peak.head(10)[[
                "observatory", "country", "peak_hour",
                "peak_score", "window_start", "window_end",
                "total_good_hours", "weather_score"
            ]].rename(columns={
                "observatory":      "Observatory",
                "country":          "Country",
                "peak_hour":        "Peak Hour",
                "peak_score":       "Peak Score",
                "window_start":     "Window Start",
                "window_end":       "Window End",
                "total_good_hours": "Good Hours",
                "weather_score":    "Weather Score"
            }),
            hide_index=True
        )

        st.download_button(
            label="Download peak times for all observatories",
            data=peak[[
                "observatory", "country", "peak_hour",
                "peak_score", "window_start", "window_end",
                "total_good_hours", "weather_score"
            ]].to_csv(index=False),
            file_name=f"peak_times_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )

# ═══════════════════════════════════════════════════════
# TAB 5 — Atmospheric Analysis
# ═══════════════════════════════════════════════════════
if selected_page == "Atmospheric Analysis":
    page_header("🌫️", "Atmospheric Analysis",
        "Seeing index, Precipitable Water Vapor (PWV), and "
        "Jet Stream impact for every observatory. "
        "Essential for professional telescope scheduling.")

    # Calculate atmospheric data for all observatories
    atm_df = load_atmospheric_cached()

    if atm_df.empty:
        st.info("Atmospheric analysis data is not available yet. "
                "Try refreshing with Fetch Live Data.")
        st.stop()

    # Summary metrics
    a1, a2, a3, a4 = st.columns(4)
    best_seeing = atm_df.iloc[0]
    best_pwv    = atm_df.sort_values(
        "pwv_mm", ascending=True).iloc[0]
    low_jet     = atm_df[
        atm_df["jet_impact"] == "Negligible"]

    a1.metric("Best Seeing",
              f"{best_seeing['seeing_arcsec']}\"",
              best_seeing["observatory"].replace(
                  " Observatory", ""))
    a2.metric("Lowest PWV",
              f"{best_pwv['pwv_mm']} mm",
              best_pwv["observatory"].replace(
                  " Observatory", ""))
    a3.metric("Calm Jet Stream Sites", len(low_jet))
    a4.metric("Observatories Analysed", len(atm_df))

    st.markdown("---")

    # World map coloured by seeing
    st.subheader("World map — atmospheric seeing index")
    st.caption(
        "Circle colour shows estimated seeing in arcseconds. "
        "Green = exceptional, Red = poor."
    )

    _atm_tile_choice = st.radio(
        "Map style",
        ["Light", "Dark", "Street (cities)", "Satellite"],
        horizontal=True,
        index=0,
        key="atm_tile",
    )
    _atm_tile_map = {
        "Light":           ("CartoDB positron",   None),
        "Dark":            ("CartoDB dark_matter", None),
        "Street (cities)": ("OpenStreetMap",       None),
        "Satellite": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        ),
    }
    _atm_tile_url, _atm_tile_attr = _atm_tile_map[_atm_tile_choice]

    if _atm_tile_choice == "Satellite":
        m_atm = folium.Map(location=[20, 0], zoom_start=2,
                           tiles=_atm_tile_url, attr=_atm_tile_attr)
    else:
        m_atm = folium.Map(
            location=[20, 0], zoom_start=2,
            tiles=_atm_tile_url
        )

    for _, row in atm_df.iterrows():
        obs_match = df[df["observatory"] == row["observatory"]]
        if obs_match.empty:
            continue
        obs_row = obs_match.iloc[0]
        color   = row["seeing_color"]

        popup_html = f"""
            <div style='font-family:sans-serif;width:220px'>
                <b>{row['observatory']}</b><br>
                {row['country']} · {row['altitude_m']}m<br>
                <hr style='margin:4px 0'>
                <b>Seeing:</b> {row['seeing_arcsec']}"
                [{row['seeing_quality']}]<br>
                <b>PWV:</b> {row['pwv_mm']} mm
                [{row['pwv_quality']}]<br>
                <b>Jet stream:</b> {row['jet_stream_ms']} m/s
                [{row['jet_impact']}]<br>
                <hr style='margin:4px 0'>
                Weather score: {row['weather_score']}/100
            </div>
        """
        folium.CircleMarker(
            location=[obs_row["latitude"],
                      obs_row["longitude"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=230),
            tooltip=f"{row['observatory']} — "
                    f"Seeing {row['seeing_arcsec']}\" "
                    f"[{row['seeing_quality']}]"
        ).add_to(m_atm)

    st_folium(m_atm, width=None, height=500)

    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    sc1.markdown("🟢 **< 0.5\"** Exceptional")
    sc2.markdown("🟩 **< 1.0\"** Excellent")
    sc3.markdown("🔵 **< 1.5\"** Good")
    sc4.markdown("🟡 **< 2.5\"** Average")
    sc5.markdown("🔴 **< 3.5\"** Poor")
    sc6.markdown("🟥 **> 3.5\"** Very Poor")

    st.markdown("---")

    with st.expander("Atmospheric rankings", expanded=False):
        # Three sub-tabs for each metric
        seeing_tab, pwv_tab, jet_tab = st.tabs([
            "👁️ Seeing Index",
            "💧 Precipitable Water Vapor",
            "🌪️ Jet Stream"
        ])

        with seeing_tab:
            st.subheader("Atmospheric seeing rankings")
            st.caption(
                "Seeing measures atmospheric turbulence. "
                "Lower arcseconds = sharper images. "
                "Professional telescopes need < 1.5\" to operate "
                "at full resolution."
            )
            for _, row in atm_df.iterrows():
                bar_val = max(0, min(1,
                    1 - (row["seeing_arcsec"] - 0.3) / 4.7))
                st.markdown(
                    f"**{row['observatory']}** — "
                    f"{row['seeing_arcsec']}\" "
                    f"[{row['seeing_quality']}] · "
                    f"{row['country']}"
                )
                st.progress(
                    bar_val,
                    text=f"Seeing {row['seeing_arcsec']}\" · "
                         f"Alt {row['altitude_m']}m · "
                         f"Wind {row.get('weather_score', 0)}/100 "
                         f"weather"
                )

        with pwv_tab:
            st.subheader("Precipitable Water Vapor rankings")
            st.caption(
                "PWV measures water vapour in the atmosphere. "
                "Critical for infrared and radio astronomy. "
                "< 2mm is excellent for IR work. "
                "Sites like ALMA require < 1mm."
            )
            pwv_sorted = atm_df.sort_values(
                "pwv_mm", ascending=True)
            for _, row in pwv_sorted.iterrows():
                bar_val = max(0, min(1,
                    1 - (row["pwv_mm"] / 30)))
                st.markdown(
                    f"**{row['observatory']}** — "
                    f"{row['pwv_mm']} mm "
                    f"[{row['pwv_quality']}] · "
                    f"{row['country']}"
                )
                st.progress(
                    bar_val,
                    text=f"PWV {row['pwv_mm']} mm · "
                         f"Altitude {row['altitude_m']}m"
                )

        with jet_tab:
            st.subheader("Jet stream impact rankings")
            st.caption(
                "The jet stream at ~10km altitude causes the worst "
                "atmospheric seeing when directly overhead. "
                "Below 20 m/s is ideal. Above 60 m/s degrades "
                "image quality severely."
            )
            jet_sorted = atm_df.sort_values(
                "jet_stream_ms", ascending=True)
            for _, row in jet_sorted.iterrows():
                js  = row["jet_stream_ms"] or 0
                bar_val = max(0, min(1, 1 - (js / 100)))
                st.markdown(
                    f"**{row['observatory']}** — "
                    f"{js} m/s "
                    f"[{row['jet_impact']}] · "
                    f"{row['country']}"
                )
                st.progress(
                    bar_val,
                    text=f"Jet stream {js} m/s · "
                         f"Impact: {row['jet_impact']}"
                )

    st.markdown("---")

    # Full atmospheric table
    st.subheader("Complete atmospheric data table")
    atm_display = atm_df[[
        "observatory", "country", "altitude_m",
        "seeing_arcsec", "seeing_quality",
        "pwv_mm", "pwv_quality",
        "jet_stream_ms", "jet_impact",
        "weather_score"
    ]].rename(columns={
        "observatory":   "Observatory",
        "country":       "Country",
        "altitude_m":    "Altitude (m)",
        "seeing_arcsec": "Seeing (\")",
        "seeing_quality":"Seeing Quality",
        "pwv_mm":        "PWV (mm)",
        "pwv_quality":   "PWV Quality",
        "jet_stream_ms": "Jet Stream (m/s)",
        "jet_impact":    "Jet Impact",
        "weather_score": "Weather Score"
    })
    st.dataframe(atm_display, hide_index=True, height=600)

    st.download_button(
        label="Download atmospheric analysis as CSV",
        data=atm_display.to_csv(index=False),
        file_name=f"atmospheric_analysis_"
                  f"{utcnow().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )
# ═══════════════════════════════════════════════════════
# TAB 6 — Historical Reliability
# ═══════════════════════════════════════════════════════
if selected_page == "Historical Reliability":
    page_header("📊", "Historical Reliability Scoring",
        "Reliability grades based on accumulated daily weather "
        "data. The longer the pipeline runs, the more accurate "
        "these scores become. Updated automatically every day.")

    days_option = st.selectbox(
        "Analysis window",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"Last {x} days"
    )

    with st.spinner(f"Loading reliability scores — last {days_option} days..."):
        hist_df = cached_reliability_scores(days_option)

    if hist_df.empty:
        st.warning(
            "Not enough historical data yet. "
            "The pipeline needs to run for at least 2 days "
            "to show trends. Check back tomorrow!"
        )
        st.info(
            "💡 Every day the pipeline runs at 06:00 UTC "
            "via GitHub Actions, adding another day of data. "
            "After 7 days you will see meaningful reliability "
            "scores. After 30 days the grades become very "
            "accurate."
        )
    else:
        # Summary metrics
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Observatories Ranked",  len(hist_df))
        h2.metric("Days of Data",
                  hist_df.iloc[0]["days_of_data"])
        h3.metric("Best Reliability Grade",
                  f"{hist_df.iloc[0]['observatory'].replace(' Observatory', '')[:20]} "
                  f"— {hist_df.iloc[0]['grade']}")
        h4.metric("Most Consistent Site",
                  hist_df.sort_values(
                      "consistency",
                      ascending=False
                  ).iloc[0]["observatory"].replace(
                      " Observatory", "")[:20])

        st.markdown("---")

        # Grade distribution
        st.subheader("Grade distribution")
        grade_counts = hist_df["grade"].value_counts()
        gc1, gc2, gc3, gc4, gc5 = st.columns(5)
        a_grades  = sum(grade_counts.get(g, 0)
                        for g in ["A+", "A", "A-"])
        b_grades  = sum(grade_counts.get(g, 0)
                        for g in ["B+", "B", "B-"])
        c_grades  = sum(grade_counts.get(g, 0)
                        for g in ["C+", "C", "C-"])
        d_grades  = grade_counts.get("D", 0)
        gc1.metric("A grades (Excellent)", a_grades)
        gc2.metric("B grades (Good)",      b_grades)
        gc3.metric("C grades (Average)",   c_grades)
        gc4.metric("D grades (Poor)",      d_grades)
        gc5.metric("Improving trend 📈",
                   len(hist_df[
                       hist_df["trend"].str.contains(
                           "Improving")]))

        st.markdown("---")

        # Rankings
        st.subheader(
            f"Reliability rankings — last {days_option} days")

        for _hist_i, (_, row) in enumerate(hist_df.iterrows()):
            grade_color = get_grade_color(row["grade"])
            trend_emoji = get_trend_emoji(row["trend"])

            with st.expander(
                f"**{row['grade']}** — "
                f"{row['observatory']} · "
                f"Reliability {row['reliability_score']}/100 · "
                f"{row['pct_excellent']}% excellent nights · "
                f"{trend_emoji} {row['trend']}"
            ):
                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Reliability Score",
                          f"{row['reliability_score']}/100")
                r2.metric("Average Score",
                          f"{row['avg_score']}/100")
                r3.metric("Consistency",
                          f"{row['consistency']}/100")
                r4.metric("% Excellent Nights",
                          f"{row['pct_excellent']}%")
                r5.metric("Days of Data",
                          row["days_of_data"])

                n1, n2, n3 = st.columns(3)
                n1.metric("Excellent Nights (80+)",
                          row["excellent_nights"])
                n2.metric("Good Nights (60+)",
                          row["good_nights"])
                n3.metric("Poor Nights (<40)",
                          row["poor_nights"])

                d1, d2, d3 = st.columns(3)
                d1.metric("Best Day",   row["best_day"])
                d2.metric("Worst Day",  row["worst_day"])
                d3.metric("Trend",      row["trend"])

                # Mini score history chart — Plotly
                if row["daily_scores"]:
                    import plotly.graph_objects as go
                    dates  = [d["fetch_date"] for d in row["daily_scores"]]
                    scores = [d["daily_score"] for d in row["daily_scores"]]
                    _mfig  = go.Figure()
                    _mfig.add_trace(go.Scatter(x=dates, y=scores, fill="tozeroy", fillcolor=f"rgba(55,138,221,0.15)", line=dict(color=grade_color, width=2), mode="lines", name="Score"))
                    _mfig.add_hline(y=80, line=dict(color="#1D9E75", dash="dash", width=1), annotation_text="Excellent", annotation_font_color="#1D9E75")
                    _mfig.add_hline(y=60, line=dict(color="#378ADD", dash="dash", width=1), annotation_text="Good", annotation_font_color="#378ADD")
                    _mfig.update_layout(
                        yaxis=dict(range=[0,105], title="Score"),
                        xaxis=dict(tickangle=45),
                        template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
                        paper_bgcolor=BG3, plot_bgcolor=BG3,
                        font=dict(color=TEXT, size=10),
                        height=180, margin=dict(l=40, r=10, t=10, b=60),
                        showlegend=False
                    )
                    st.plotly_chart(_mfig, use_container_width=True,
                                    key=f"reliab_chart_{_hist_i}")

                st.caption(
                    f"{row['country']} · "
                    f"{row['altitude_m']}m altitude · "
                    f"Score range: {row['min_score']} — "
                    f"{row['max_score']}"
                )

        st.markdown("---")

        # Full table
        st.subheader("Complete reliability table")
        hist_display = hist_df[[
            "observatory", "country", "grade",
            "reliability_score", "avg_score",
            "consistency", "pct_excellent",
            "pct_good", "pct_poor",
            "days_of_data", "trend"
        ]].rename(columns={
            "observatory":       "Observatory",
            "country":           "Country",
            "grade":             "Grade",
            "reliability_score": "Reliability",
            "avg_score":         "Avg Score",
            "consistency":       "Consistency",
            "pct_excellent":     "% Excellent",
            "pct_good":          "% Good",
            "pct_poor":          "% Poor",
            "days_of_data":      "Days",
            "trend":             "Trend"
        })
        st.dataframe(hist_display, hide_index=True,
                     height=600)

        st.download_button(
            label="Download reliability report as CSV",
            data=hist_display.to_csv(index=False),
            file_name=f"reliability_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )
# ═══════════════════════════════════════════════════════
# TAB 7 — Site Comparison
# ═══════════════════════════════════════════════════════
if selected_page == "Site Comparison":
    page_header("⚖️", "Comparative Site Analysis",
        "Select 2 to 5 observatories to compare side by side. "
        "Useful for telescope time proposals and site selection. "
        "Combines current conditions, historical reliability, "
        "atmospheric seeing, PWV, and jet stream impact.")

    # Observatory selector
    all_obs = df["observatory"].tolist()
    selected_sites = st.multiselect(
        "Select observatories to compare (2–5)",
        all_obs,
        default=all_obs[:3],
        max_selections=5
    )

    comp_days = st.selectbox(
        "Historical window",
        [7, 14, 30],
        index=0,
        format_func=lambda x: f"Last {x} days",
        key="comp_days"
    )

    if len(selected_sites) < 2:
        st.warning(
            "Please select at least 2 observatories to compare.")
    else:
        with st.spinner(f"Comparing {len(selected_sites)} sites..."):
            comp_df = cached_compare_sites(tuple(selected_sites), comp_days)

        if comp_df.empty:
            st.error("Could not load comparison data.")
        else:
            st.markdown("---")

            # ── Current conditions comparison ─────────────────
            st.subheader("Current conditions")
            cols = st.columns(len(comp_df))
            for i, (_, row) in enumerate(comp_df.iterrows()):
                with cols[i]:
                    score = row["today_score"]
                    if score >= 80:   color = "🟢"
                    elif score >= 60: color = "🔵"
                    elif score >= 40: color = "🟡"
                    else:             color = "🔴"
                    st.markdown(
                        f"### {color} {row['observatory'].replace(' Observatory', '').replace(' Telescope', '')[:20]}")
                    st.metric("Today's Score",
                              f"{score}/100")
                    st.metric("Cloud Cover",
                              f"{row['cloud_cover_pct']}%")
                    st.metric("Humidity",
                              f"{row['humidity_pct']}%")
                    st.metric("Wind Speed",
                              f"{row['wind_speed_ms']} m/s")
                    st.metric("Temperature",
                              f"{row['temperature_c']}°C")

            st.markdown("---")

            # ── Atmospheric comparison ────────────────────────
            st.subheader("Atmospheric conditions")
            cols2 = st.columns(len(comp_df))
            for i, (_, row) in enumerate(comp_df.iterrows()):
                with cols2[i]:
                    st.markdown(
                        f"**{row['observatory'].replace(' Observatory', '')[:20]}**")
                    st.metric("Seeing",
                              f"{row['seeing_arcsec']}\"",
                              row["seeing_quality"])
                    st.metric("PWV",
                              f"{row['pwv_mm']} mm",
                              row["pwv_quality"])
                    st.metric("Jet Stream",
                              f"{row['jet_stream_ms']} m/s",
                              row["jet_impact"])
                    st.metric("Altitude",
                              f"{row['altitude_m']}m")

            st.markdown("---")

            # ── Historical comparison chart ───────────────────
            st.subheader(
                f"Score history — last {comp_days} days")

            import plotly.graph_objects as go
            colors_palette = ["#1D9E75","#378ADD","#EF9F27","#E24B4A","#AFA9EC"]
            _hfig = go.Figure()
            has_history = False
            for i, (_, row) in enumerate(comp_df.iterrows()):
                if row["daily_scores"]:
                    has_history = True
                    dates  = [d["fetch_date"] for d in row["daily_scores"]]
                    scores = [d["daily_score"] for d in row["daily_scores"]]
                    color  = colors_palette[i % len(colors_palette)]
                    label  = row["observatory"].replace(" Observatory","").replace(" Telescope","")[:25]
                    _hfig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", line=dict(color=color, width=2), marker=dict(size=4), fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)", name=label))
            if has_history:
                _hfig.add_hline(y=80, line=dict(color="#1D9E75", dash="dash", width=1))
                _hfig.add_hline(y=60, line=dict(color="#378ADD", dash="dash", width=1))
                _hfig.update_layout(
                    title="Historical Score Comparison", yaxis=dict(range=[0,105], title="Observation Score"),
                    xaxis=dict(tickangle=45),
                    template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
                    paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
                    height=420, margin=dict(l=40,r=20,t=60,b=80),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(_hfig, use_container_width=True)
            else:
                st.info("Not enough historical data yet. Come back after a few days of pipeline runs to see score trends here.")

            st.markdown("---")

            # ── Bar chart comparison ──────────────────────────
            st.subheader("Side by side metrics comparison")

            metrics = {
                "Today's Score":    "today_score",
                "Avg Score":        "avg_score",
                "% Excellent":      "pct_excellent",
                "Consistency":      "consistency",
                "Seeing (inverted)": "seeing_arcsec",
                "PWV (inverted)":   "pwv_mm"
            }

            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            names = [r["observatory"].replace(" Observatory","").replace(" Telescope","")[:15] for _, r in comp_df.iterrows()]
            _cfig = make_subplots(rows=2, cols=3, subplot_titles=list(metrics.keys()))
            for idx, (label, col) in enumerate(metrics.items()):
                row_i, col_i = divmod(idx, 3)
                vals = comp_df[col].tolist()
                plot_vals = [max(0,100-v*10) if "inverted" in label and v is not None else (v if v is not None else 0) for v in vals]
                bar_colors = [colors_palette[i % len(colors_palette)] for i in range(len(names))]
                _cfig.add_trace(go.Bar(x=names, y=plot_vals, marker_color=bar_colors, showlegend=False, hovertemplate="%{x}<br>%{y:.1f}<extra></extra>"), row=row_i+1, col=col_i+1)
            _cfig.update_layout(
                title="Observatory Comparison Dashboard",
                template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
                paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
                height=600, margin=dict(l=40,r=20,t=80,b=40)
            )
            st.plotly_chart(_cfig, use_container_width=True)

            st.markdown("---")

            # ── Full comparison table ─────────────────────────
            st.subheader("Full comparison table")
            comp_display = comp_df[[
                "observatory", "country", "altitude_m",
                "today_score", "avg_score", "pct_excellent",
                "consistency", "seeing_arcsec", "pwv_mm",
                "jet_stream_ms", "jet_impact", "days_of_data"
            ]].rename(columns={
                "observatory":   "Observatory",
                "country":       "Country",
                "altitude_m":    "Altitude (m)",
                "today_score":   "Today",
                "avg_score":     "Avg Score",
                "pct_excellent": "% Excellent",
                "consistency":   "Consistency",
                "seeing_arcsec": "Seeing (\")",
                "pwv_mm":        "PWV (mm)",
                "jet_stream_ms": "Jet (m/s)",
                "jet_impact":    "Jet Impact",
                "days_of_data":  "Days"
            })
            st.dataframe(comp_display,
                         hide_index=True, height=300)

            # Download
            st.download_button(
                label="Download comparison as CSV",
                data=comp_display.to_csv(index=False),
                file_name=f"site_comparison_"
                          f"{utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )

            # ── Proposal helper text ──────────────────────────
            st.markdown("---")
            st.subheader("📝 Proposal helper")
            st.caption(
                "Auto-generated text you can use in a telescope "
                "time proposal to justify your site selection."
            )

            best = comp_df.iloc[0]
            proposal_text = f"""
Based on atmospheric monitoring data collected over the past {comp_days} days, {best['observatory']} demonstrates superior observing conditions compared to the {len(comp_df)-1} alternative site(s) considered.

{best['observatory']} achieved an average observation quality score of {best['avg_score']}/100, with {best['pct_excellent']}% of monitored nights classified as excellent (score ≥ 80). The estimated atmospheric seeing of {best['seeing_arcsec']} arcseconds and precipitable water vapor of {best['pwv_mm']} mm place this site in the {best['seeing_quality']} category for optical observation quality.

The jet stream impact at this site is currently assessed as {best['jet_impact']} at {best['jet_stream_ms']} m/s at 250hPa, indicating {'minimal' if best['jet_impact'] in ['Negligible', 'Low'] else 'moderate to significant'} upper-atmosphere turbulence.

At {best['altitude_m']}m elevation in {best['country']}, this site {'benefits from reduced atmospheric water vapor compared to lower-altitude alternatives' if best['altitude_m'] > 2000 else 'provides accessible infrastructure while maintaining acceptable atmospheric conditions'}.

Data sourced from automated atmospheric monitoring pipeline (Open-Meteo API) with daily updates via GitHub Actions.
            """.strip()

            st.text_area(
                "Copy this into your proposal",
                proposal_text,
                height=250
            )

# ═══════════════════════════════════════════════════════
# Observing Proposal Planner
# ═══════════════════════════════════════════════════════
if selected_page == "Observing Proposal Planner":
    page_header("📝", "Observing Proposal Planner",
        "Assemble the core of a professional observing proposal — target "
        "list with coordinates and magnitudes, required observing time, "
        "moon phase and date, and full signal-to-noise / exposure "
        "calculations. Export a draft you can build on.")

    from object_visibility import OBJECTS, calculate_visibility
    from snr_calculator import (OBJECT_MAGNITUDES, PHOTOMETRIC_FILTERS,
                                calculate_snr, get_telescope_specs,
                                get_sky_brightness)

    # B−V colours for the brighter, well-characterised stars (§6).
    # "—" elsewhere — we don't fabricate values we don't have.
    _BV_COLOURS = {
        "Sirius": 0.00, "Canopus": 0.15, "Arcturus": 1.23, "Vega": 0.00,
        "Capella": 0.80, "Rigel": -0.03, "Betelgeuse": 1.85,
        "Polaris": 0.60, "Antares": 1.83, "Aldebaran": 1.54,
        "Spica": -0.23, "Fomalhaut": 0.09, "Deneb": 0.09,
    }

    # ── §1–2 Title & summary (user input) ──────────────
    pp_title = st.text_input("Title of observing programme (§1, ≤12 words)",
        key="pp_title", placeholder="e.g. Photometric monitoring of bright variable stars")
    pp_summary = st.text_area("Summary of proposed observations (§2, ≤150 words)",
        key="pp_summary", height=80,
        placeholder="Briefly describe what you will observe and why.")

    st.markdown("---")

    # ── 1. Site + instrument ───────────────────────────
    pp_c1, pp_c2, pp_c3 = st.columns(3)
    with pp_c1:
        pp_site = st.selectbox("Observatory",
            df["observatory"].tolist(), key="pp_site")
    pp_row = df[df["observatory"] == pp_site].iloc[0]
    pp_alt_m = float(pp_row.get("altitude_m", 0) or 0)
    with pp_c2:
        pp_filter_name = st.selectbox("Filter / band",
            list(PHOTOMETRIC_FILTERS.keys()), index=2, key="pp_filter")
    pp_filt = PHOTOMETRIC_FILTERS[pp_filter_name]
    with pp_c3:
        pp_target_snr = st.slider("Target SNR", 5, 200, 30, 5,
            key="pp_target_snr",
            help="Exposure time is solved to reach this SNR per target.")

    # ── 2. Moon phase required (§4) ─────────────────────
    pp_moon_choice = st.radio("Required moon conditions (§4)",
        ["Dark (new moon)", "Grey (quarter)", "Bright (full)"],
        horizontal=True, key="pp_moon")
    _moon_map = {"Dark (new moon)": (5, 0),
                 "Grey (quarter)": (50, 30),
                 "Bright (full)": (100, 60)}
    _moon_pct, _moon_alt = _moon_map[pp_moon_choice]
    pp_sky_mag = get_sky_brightness(_moon_pct, _moon_alt)

    # ── 3. Target selection ─────────────────────────────
    _targetable = [k for k in OBJECT_MAGNITUDES.keys() if k in OBJECTS]
    pp_targets = st.multiselect(
        "Select targets (§6)", _targetable,
        default=_targetable[:3] if len(_targetable) >= 3 else _targetable,
        key="pp_targets")

    if not pp_targets:
        st.info("Select one or more targets to build the proposal.")
        st.stop()

    specs = get_telescope_specs(pp_site, pp_alt_m)

    def _solve_exposure(mag, name, alt_deg):
        """Bisection: shortest exposure (s) to reach target SNR."""
        lo, hi = 1.0, 36000.0
        def snr_at(t):
            r = calculate_snr(
                object_magnitude=mag, exposure_time_s=t,
                telescope_specs=specs, sky_brightness_mag=pp_sky_mag,
                seeing_arcsec=1.0, object_name=name,
                object_altitude_deg=alt_deg, site_altitude_m=pp_alt_m,
                filter_band=pp_filt["band"],
                wavelength_nm=pp_filt["wavelength_nm"],
                bandwidth_nm=pp_filt["bandwidth_nm"])
            return r["snr"]
        if snr_at(hi) < pp_target_snr:
            return None  # not reachable within 10 h
        for _ in range(40):
            mid = (lo + hi) / 2
            if snr_at(mid) >= pp_target_snr:
                hi = mid
            else:
                lo = mid
        return hi

    rows = []
    for t in pp_targets:
        info = OBJECTS.get(t, {})
        mag  = OBJECT_MAGNITUDES.get(t)
        vis  = calculate_visibility(pp_row["latitude"], pp_row["longitude"],
                                    t, altitude_m=pp_alt_m)
        alt  = vis["altitude_deg"] if vis else 0
        exp  = _solve_exposure(mag, t, max(alt, 20)) if mag is not None else None
        _bv  = _BV_COLOURS.get(t)
        rows.append({
            "Target": t,
            "RA (J2000)": info.get("ra", "—"),
            "Dec (J2000)": info.get("dec", "—"),
            "V mag": mag if mag is not None else "—",
            "B−V": _bv if _bv is not None else "—",
            "Altitude now (°)": alt,
            "Airmass": vis["airmass"] if vis else None,
            "Exposure (s)": round(exp, 0) if exp else "Not reachable",
        })
    pp_table = pd.DataFrame(rows)

    # ── Target table (§6) ───────────────────────────────
    st.subheader("Target list (§6)")
    st.caption("Coordinates are J2000 equinox/epoch. B−V shown where "
               "catalogued; exposures solved to your target SNR.")
    st.dataframe(pp_table, hide_index=True, use_container_width=True)

    # ── §5 Preferred date/time ─────────────────────────
    # Best dark hour tonight for the targets, from the peak-time engine.
    from peak_time import get_peak_time
    _best_hours = []
    for t in pp_targets:
        try:
            pk = get_peak_time(pp_row["latitude"], pp_row["longitude"],
                float(pp_row.get("observation_score", 50) or 50),
                object_name=t, altitude_m=pp_alt_m)
            if pk and pk.get("peak_hour"):
                _best_hours.append(pk["peak_hour"])
        except Exception:
            continue
    _pref_time = (max(set(_best_hours), key=_best_hours.count)
                  if _best_hours else "Any dark hour")

    # ── Time / moon / date summary (§3, §4, §5) ─────────
    _exps = [r["Exposure (s)"] for r in rows
             if isinstance(r["Exposure (s)"], (int, float))]
    _total_s = sum(_exps) if _exps else 0
    # Add ~40% overhead for slew/readout/acquisition.
    _total_h = round(_total_s * 1.4 / 3600, 2)

    st.subheader("Time, moon & date (§3–5)")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Observing time required (§3)", f"{_total_h} h",
              help="Sum of exposures + 40% overhead.")
    s2.metric("Moon phase required (§4)", pp_moon_choice.split(" ")[0])
    s3.metric("Preferred time (§5)", _pref_time,
              help="Dark hour tonight when the targets are best placed.")
    s4.metric("Filter / band", pp_filt["band"])

    # ── §7 Finding charts note ─────────────────────────
    st.info("**Finding charts (§7)** must be made externally — generate "
            "~5′ fields (N up, E left) from Aladin Lite, the STScI DSS, or "
            "SkyView using each target's J2000 coordinates above. GOWC has "
            "no image-survey access.", icon="🗺️")

    # ── §10–11 user input ──────────────────────────────
    pp_b1, pp_b2 = st.columns(2)
    with pp_b1:
        pp_backup = st.text_area("Backup programme (§10, ≤50 words)",
            key="pp_backup", height=80,
            placeholder="What you'd do in poor seeing/cirrus — e.g. observe "
                        "only the brightest targets.")
    with pp_b2:
        pp_experience = st.text_area("Previous experience (§11, ≤50 words)",
            key="pp_experience", height=80,
            placeholder="Your prior observing experience.")

    # ── Exportable draft (all sections) ────────────────
    st.subheader("Proposal draft")
    _draft_lines = [
        "OBSERVING PROPOSAL (draft)",
        "=" * 50, "",
        f"§1 TITLE: {pp_title or '[to complete]'}",
        "",
        f"§2 SUMMARY:",
        f"  {pp_summary or '[to complete — max 150 words]'}",
        "",
        f"§3 OBSERVING TIME REQUIRED : {_total_h} hours (incl. ~40% overhead)",
        f"§4 MOON PHASE REQUIRED     : {pp_moon_choice}",
        f"§5 PREFERRED DATE/TIME     : tonight around {_pref_time} (dark, targets well placed)",
        "",
        f"Observatory                : {pp_site} ({int(pp_alt_m)} m)",
        f"Filter / band              : {pp_filter_name}",
        f"Target SNR                 : {pp_target_snr}",
        "",
        "§6 TARGET LIST (J2000):",
    ]
    for r in rows:
        _draft_lines.append(
            f"  {r['Target']}  RA {r['RA (J2000)']}  Dec {r['Dec (J2000)']}  "
            f"V={r['V mag']}  B-V={r['B−V']}  exp={r['Exposure (s)']}s  "
            f"(alt {r['Altitude now (°)']}°, X={r['Airmass']})")
    _draft_lines += [
        "",
        "§7 FINDING CHARTS: produce externally (Aladin/DSS), ~5' N-up E-left.",
        "",
        "§8 SCIENTIFIC JUSTIFICATION: [~2000 words — your own work]",
        "",
        "§9 TECHNICAL JUSTIFICATION:",
        f"  Exposure times solved via the CCD signal-to-noise equation",
        f"  (shot + sky + dark + read + scintillation noise) in the "
        f"{pp_filt['band']} band, including airmass extinction at "
        f"{int(pp_alt_m)} m and moon-dependent sky brightness "
        f"({pp_sky_mag} mag/arcsec²).",
        "",
        f"§10 BACKUP PROGRAMME: {pp_backup or '[to complete — max 50 words]'}",
        "",
        f"§11 PREVIOUS EXPERIENCE: {pp_experience or '[to complete — max 50 words]'}",
        "",
        "Generated by GOWC — gowcastroclimate.com",
    ]
    _draft = "\n".join(_draft_lines)
    st.code(_draft, language="text")
    st.download_button("Download proposal draft (.txt)", _draft,
        file_name=f"observing_proposal_{utcnow().strftime('%Y-%m-%d')}.txt",
        mime="text/plain")

    st.caption("Sections 3–7, 9 are computed/structured for you. "
               "Sections 1, 2, 8, 10, 11 are your own input (the science "
               "case especially must be your own work).")


# ═══════════════════════════════════════════════════════
# Semester Planning Calendar — now a section of the planner,
# aids the §5 "preferred date/time" decision across months.
# ═══════════════════════════════════════════════════════
if selected_page == "Observing Proposal Planner":
    st.markdown("---")
    st.subheader("📅 Best months / semester calendar (§5 aid)")
    st.caption(
        "Plan months in advance. Shows predicted observation quality for "
        "every day based on moon phase and dark hours — use it to pick the "
        "best date for §5. Actual recorded scores shown where available."
    )

    # Controls
    sp1, sp2, sp3 = st.columns(3)
    with sp1:
        sem_obs = st.selectbox(
            "Select observatory",
            df["observatory"].tolist(),
            key="sem_obs"
        )
    with sp2:
        current_year = utcnow().year
        sem_year = st.selectbox(
            "Year",
            [current_year, current_year + 1],
            key="sem_year"
        )
    with sp3:
        sem_months = st.selectbox(
            "Months to show",
            [3, 6, 9, 12],
            index=1,
            key="sem_months"
        )

    start_month = st.selectbox(
        "Starting month",
        list(range(1, 13)),
        index=utcnow().month - 1,
        format_func=lambda x: calendar.month_name[x],
        key="sem_start"
    )

    with st.spinner(f"Building {sem_months}-month calendar for {sem_obs}..."):
        cal_data    = cached_calendar_data(sem_obs, sem_year, start_month, sem_months)
        best_months = cached_best_months(sem_obs, sem_year, sem_months)

    if best_months is None or best_months.empty:
        st.info("Not enough data to build a semester plan for this "
                "selection yet. Try a different observatory or year.")
        st.stop()

    st.markdown("---")

    # Best months summary
    st.subheader("Best months for observing")
    bm_cols = st.columns(min(4, len(best_months)))
    for i, (_, row) in enumerate(
        best_months.head(4).iterrows()
    ):
        with bm_cols[i]:
            st.metric(
                row["month"],
                f"{row['excellent_days']} excellent days",
                f"Avg {row['avg_score']}/100"
            )

    st.markdown("---")

    # Monthly bar chart — Plotly
    import plotly.graph_objects as go
    import calendar as cal_module
    month_names = best_months["month"].tolist()
    exc_days    = best_months["excellent_days"].tolist()
    good_days   = best_months["good_days"].tolist()
    _sfig = go.Figure()
    _sfig.add_trace(go.Bar(name="Excellent nights", x=month_names, y=exc_days, marker_color="#1D9E75"))
    _sfig.add_trace(go.Bar(name="Good nights", x=month_names, y=good_days, marker_color="#378ADD"))
    _sfig.update_layout(
        title=f"Observing Quality by Month — {sem_obs}",
        barmode="group", yaxis_title="Number of nights",
        template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
        paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
        height=360, margin=dict(l=40,r=20,t=60,b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(_sfig, use_container_width=True)

    st.markdown("---")

    # Calendar heatmap for each month
    st.subheader("Day by day calendar heatmap")
    st.caption(
        "🟢 Excellent · 🔵 Good · 🟡 Marginal · 🔴 Poor · "
        "Bold = actual recorded data · Normal = estimated"
    )

    color_map = {
        "Excellent": "#1D9E75",
        "Good":      "#378ADD",
        "Marginal":  "#EF9F27",
        "Poor":      "#E24B4A"
    }

    for month_key, month_data in cal_data.items():
        st.markdown(
            f"### {month_data['month_name']} "
            f"{month_data['year']}"
        )

        summary = month_data["summary"]
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Avg Score",
                   f"{summary['avg_score']}/100")
        sc2.metric("Excellent Days",
                   summary["excellent_days"])
        sc3.metric("Good Days",
                   summary["good_days"])
        sc4.metric("New Moon Days",
                   summary["new_moon_days"])

        # Build calendar grid
        days      = month_data["days"]
        first_day = days[0]["weekday"]

        # Header
        day_cols = st.columns(7)
        for i, d in enumerate(
            ["Mon", "Tue", "Wed", "Thu",
             "Fri", "Sat", "Sun"]
        ):
            day_cols[i].markdown(
                f"<div style='text-align:center;"
                f"color:#888780;font-size:12px'>"
                f"<b>{d}</b></div>",
                unsafe_allow_html=True
            )

        # Calendar rows
        week_days = [None] * first_day + days
        while len(week_days) % 7 != 0:
            week_days.append(None)

        for week_start in range(
            0, len(week_days), 7
        ):
            week = week_days[week_start:week_start + 7]
            cols = st.columns(7)
            for i, day_data in enumerate(week):
                if day_data is None:
                    cols[i].markdown(" ")
                else:
                    color    = color_map.get(
                        day_data["quality"], "#888780")
                    score    = day_data["moon_adj_score"]
                    day_num  = day_data["day"]
                    moon_pct = day_data["moon_pct"]
                    is_today = (
                        day_data["date"] ==
                        utcnow().strftime(
                            "%Y-%m-%d"))
                    border   = (
                        "3px solid white"
                        if is_today
                        else "1px solid #333"
                    )
                    actual   = "★" if day_data[
                        "is_actual"] else ""

                    cols[i].markdown(
                        f"<div style='"
                        f"background:{color}22;"
                        f"border:{border};"
                        f"border-radius:6px;"
                        f"padding:4px;"
                        f"text-align:center;"
                        f"margin:1px'>"
                        f"<span style='color:{color};"
                        f"font-weight:bold;"
                        f"font-size:13px'>"
                        f"{day_num}{actual}</span><br>"
                        f"<span style='font-size:10px;"
                        f"color:#ccc'>{score}</span><br>"
                        f"<span style='font-size:9px;"
                        f"color:#888'>"
                        f"🌙{moon_pct:.0f}%</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        st.markdown("---")

    # Semester recommendation
    st.subheader("📝 Semester recommendation")
    best_m   = best_months.iloc[0]
    worst_m  = best_months.iloc[-1]
    obs_name = sem_obs.replace(" Observatory", "").replace(
        " Telescope", "")

    recommendation = f"""
SEMESTER OBSERVING RECOMMENDATION — {sem_obs.upper()}

Best semester: {best_m['month']} {best_m['year']}
— {best_m['excellent_days']} excellent nights expected
— {best_m['good_days']} good nights expected
— Average quality score: {best_m['avg_score']}/100
— Best single night: {best_m['best_day']}

Avoid: {worst_m['month']} {worst_m['year']}
— Only {worst_m['excellent_days']} excellent nights expected
— Average quality score: {worst_m['avg_score']}/100

Key scheduling notes:
— New moon periods offer the darkest skies for faint objects
— Plan deep sky observations around new moon ± 5 days
— Bright object work (planets, doubles) can use any phase
— Allow 20% buffer for unexpected poor weather nights

Data confidence: {'High — based on actual recorded data' 
if any(d['is_actual'] for month in cal_data.values() 
       for d in month['days']) 
else 'Estimated — based on astronomical calculations'}

Generated by Global Observatory Weather Tracker
{utcnow().strftime('%Y-%m-%d %H:%M')} UTC
    """.strip()

    st.text_area(
        "Copy for your proposal or planning document",
        recommendation,
        height=300
    )

    st.download_button(
        label="Download semester plan as CSV",
        data=best_months.to_csv(index=False),
        file_name=f"semester_plan_{sem_obs.replace(' ', '_')}_"
                  f"{sem_year}.csv",
        mime="text/csv"
    )

# ═══════════════════════════════════════════════════════
# TAB 9 — Educational Mode
# ═══════════════════════════════════════════════════════
if selected_page == "Learn Astronomy":
    page_header("🎓", "Learn Astronomy — Educational Mode",
        "Understand every metric on this dashboard. "
        "From cloud cover to jet streams — explained for "
        "students, educators, and curious minds.")

    categories = get_concepts_by_category()
    concepts   = get_all_concepts()

    # Category filter
    selected_category = st.selectbox(
        "Browse by category",
        ["All"] + list(categories.keys())
    )

    if selected_category == "All":
        concept_keys = list(concepts.keys())
    else:
        concept_keys = categories[selected_category]

    st.markdown("---")

    # Search
    search = st.text_input(
        "🔍 Search concepts",
        placeholder="e.g. seeing, humidity, moon..."
    )

    if search:
        concept_keys = [
            k for k in concept_keys
            if search.lower() in k.lower()
            or search.lower() in concepts[k][
                "title"].lower()
            or search.lower() in concepts[k][
                "simple"].lower()
        ]

    if not concept_keys:
        st.warning(
            "No concepts found. Try a different search term.")
    else:
        # Quick reference cards
        st.subheader(
            f"{'All concepts' if selected_category == 'All' else selected_category} "
            f"— {len(concept_keys)} topics"
        )

        for key in concept_keys:
            concept = concepts[key]
            with st.expander(
                f"{concept['emoji']} "
                f"**{concept['title']}** — "
                f"{concept['simple']}"
            ):
                col_left, col_right = st.columns([2, 1])

                with col_left:
                    st.markdown("**What it means**")
                    st.markdown(concept["simple"])
                    st.markdown("---")
                    st.markdown("**In depth**")
                    st.markdown(concept["detailed"])

                with col_right:
                    st.markdown("**Quick reference**")
                    st.info(
                        f"**Unit:** {concept['symbol']}\n\n"
                        f"**Role:** {concept['weight']}"
                    )
                    if concept.get("formula"):
                        st.markdown("**Formula used**")
                        st.code(concept["formula"])
                    if concept.get("fun_fact"):
                        st.success(
                            f"💡 **Did you know?**\n\n"
                            f"{concept['fun_fact']}"
                        )

    st.markdown("---")

    # Live explainer — connect concepts to real data
    st.subheader(
        "🔴 Live — understand tonight's data")
    st.caption(
        "See exactly how each concept applies to "
        "real conditions right now."
    )

    live_obs = st.selectbox(
        "Pick an observatory to explain",
        df["observatory"].tolist(),
        key="edu_obs"
    )

    live_row = df[
        df["observatory"] == live_obs].iloc[0]
    score    = live_row["observation_score"]
    cloud    = live_row["cloud_cover_pct"]
    humidity = live_row["humidity_pct"]
    wind     = live_row["wind_speed_ms"]
    temp     = live_row["temperature_c"]

    st.markdown(
        f"### {live_obs} — right now")

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Score", f"{score}/100")
    e2.metric("Cloud", f"{cloud}%")
    e3.metric("Humidity", f"{humidity}%")
    e4.metric("Wind", f"{wind} m/s")

    st.markdown("---")
    st.markdown("**What this means in plain English:**")

    # Cloud explanation
    if cloud <= 10:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — the sky is essentially clear. This is ideal for all types of observation."
    elif cloud <= 30:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — mostly clear with some thin cloud. Faint objects may be slightly affected."
    elif cloud <= 60:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — partly cloudy. Only bright objects like planets and bright stars are reliable targets tonight."
    else:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — heavily clouded. The dome at this observatory would likely be closed right now."
    st.info(cloud_msg)

    # Humidity explanation
    if humidity <= 50:
        hum_msg = f"💧 Humidity is {humidity}% — very dry air. Mirrors and lenses are safe from condensation. Excellent transparency."
    elif humidity <= 70:
        hum_msg = f"💧 Humidity is {humidity}% — acceptable. No immediate risk to optics but worth monitoring."
    elif humidity <= 85:
        hum_msg = f"💧 Humidity is {humidity}% — getting high. Operators will be watching carefully. Dew heaters on the telescope will be active."
    else:
        hum_msg = f"💧 Humidity is {humidity}% — above the 85% safety threshold. Real observatories would close or have already closed the dome to protect the mirrors."
    st.info(hum_msg)

    # Wind explanation
    if wind <= 5:
        wind_msg = f"💨 Wind is {wind} m/s — essentially calm. No mechanical vibration. Images will be sharp and stable."
    elif wind <= 10:
        wind_msg = f"💨 Wind is {wind} m/s — light breeze. Negligible effect on most telescopes. Larger dishes may show very slight motion."
    elif wind <= 15:
        wind_msg = f"💨 Wind is {wind} m/s — moderate wind. Smaller telescopes may show vibration. Large professional scopes can still operate."
    else:
        wind_msg = f"💨 Wind is {wind} m/s — above the 15 m/s threshold used in our scoring. Most professional observatories would close or restrict operations at this wind speed."
    st.info(wind_msg)

    # Score explanation
    if score >= 80:
        score_msg = f"⭐ Overall score is {score}/100 — Excellent. This is a good night for serious astronomy. Deep sky objects, faint galaxies, and nebulae are all viable targets."
    elif score >= 60:
        score_msg = f"⭐ Overall score is {score}/100 — Good. Suitable for most observation programmes. Bright targets will be sharp and photometry is reliable."
    elif score >= 40:
        score_msg = f"⭐ Overall score is {score}/100 — Marginal. Only bright targets recommended. Students can still observe planets and the Moon, but faint deep sky work is not advised."
    else:
        score_msg = f"⭐ Overall score is {score}/100 — Poor. Observing is not recommended tonight at this site. A real observatory operator would keep the dome closed."
    st.success(score_msg)

    st.markdown("---")

    # Glossary
    st.subheader("📖 Quick glossary")
    glossary = {
        "Arcsecond (\")":      "1/3600 of a degree. Unit for measuring very small angles in the sky.",
        "Aperture":            "The diameter of a telescope's main mirror or lens. Larger = more light collected.",
        "Seeing":              "Atmospheric turbulence that blurs stellar images. Measured in arcseconds.",
        "PWV":                 "Precipitable Water Vapor. Total water in atmosphere above telescope. Critical for infrared.",
        "Photometry":          "Precise measurement of a star's brightness. Requires stable, clear conditions.",
        "Spectroscopy":        "Splitting starlight into its spectrum to measure composition, temperature, velocity.",
        "Limiting magnitude":  "The faintest star visible under given conditions. Higher number = fainter stars seen.",
        "Inversion layer":     "A layer of warm air trapping cool air below. Mauna Kea sits above Hawaii's inversion layer.",
        "Dome seeing":         "Turbulence caused by warm air inside the telescope dome mixing with cold outside air.",
        "Meridian":            "The imaginary line across the sky directly overhead, north to south. Objects are highest here.",
        "Zenith":              "The point directly overhead. Objects at zenith have the least atmosphere to look through.",
        "Airmass":             "How much atmosphere the telescope looks through. 1.0 at zenith, increases toward horizon.",
        "Declination":         "Celestial equivalent of latitude. How far north or south of the celestial equator.",
        "Right Ascension":     "Celestial equivalent of longitude. Measured in hours, minutes, seconds.",
        "Altitude":            "Height above the horizon in degrees. 0° = horizon, 90° = zenith.",
        "Azimuth":             "Compass direction of an object. 0° = North, 90° = East, 180° = South, 270° = West.",
    }

    for term, definition in glossary.items():
        st.markdown(f"**{term}** — {definition}")

# ═══════════════════════════════════════════════════════
# TAB 10 — Alert Subscriptions
# ═══════════════════════════════════════════════════════
if selected_page == "Alert Subscriptions":
    page_header("🔔", "Alert Subscriptions",
        "Get emailed automatically when observing conditions "
        "at your chosen observatory cross a threshold. "
        "Alerts are checked daily at 06:00 UTC.")

    # ── Subscribe form ────────────────────────────────────
    st.subheader("Subscribe to alerts")
    with st.form("subscribe_form"):
        sub_email = st.text_input(
            "Your email address",
            placeholder="you@example.com"
        )
        sub_obs = st.selectbox(
            "Observatory to monitor",
            df["observatory"].tolist(),
            key="sub_obs"
        )
        sub_threshold = st.slider(
            "Alert threshold (score)",
            min_value=40,
            max_value=95,
            value=80,
            step=5,
            help="You will be alerted when the score crosses this value"
        )
        sub_type = st.radio(
            "Alert me when score is",
            ["Above threshold (good conditions)",
             "Below threshold (poor conditions)"],
            help="Above = notify when it gets good. Below = notify when it gets bad."
        )
        submitted = st.form_submit_button(
            "Subscribe", type="primary")

        if submitted:
            if not sub_email or "@" not in sub_email:
                st.error(
                    "Please enter a valid email address.")
            else:
                alert_type = (
                    "above"
                    if "Above" in sub_type
                    else "below"
                )
                success, msg = add_subscription(
                    sub_email, sub_obs,
                    sub_threshold, alert_type
                )
                if success:
                    st.success(
                        f"✅ Subscribed! You will receive "
                        f"an email when {sub_obs} scores "
                        f"{'above' if alert_type == 'above' else 'below'} "
                        f"{sub_threshold}/100."
                    )
                else:
                    st.warning(msg)

    st.markdown("---")

    # ── Unsubscribe ───────────────────────────────────────
    st.subheader("Unsubscribe")
    with st.form("unsubscribe_form"):
        unsub_email = st.text_input(
            "Your email address",
            placeholder="you@example.com",
            key="unsub_email"
        )
        unsub_obs = st.selectbox(
            "Observatory",
            df["observatory"].tolist(),
            key="unsub_obs"
        )
        unsub_submitted = st.form_submit_button(
            "Unsubscribe")

        if unsub_submitted:
            removed = remove_subscription(
                unsub_email, unsub_obs)
            if removed:
                st.success(
                    f"✅ Unsubscribed from {unsub_obs}.")
            else:
                st.error(
                    "Subscription not found.")

    st.markdown("---")

    # ── Current subscriptions ─────────────────────────────
    st.subheader("Active subscriptions")
    subs = load_subscriptions()

    if not subs:
        st.info(
            "No active subscriptions yet. "
            "Be the first to subscribe above!")
    else:
        active = [s for s in subs if s.get("active", True)]
        st.metric("Total subscriptions", len(active))

        for sub in active:
            obs_score = df[
                df["observatory"] == sub["observatory"]
            ]
            current_score = (
                obs_score.iloc[0]["observation_score"]
                if not obs_score.empty else "N/A"
            )
            alert_type = sub.get("alert_type", "above")

            with st.expander(
                f"📧 {sub['email']} → "
                f"{sub['observatory']} · "
                f"{'Above' if alert_type == 'above' else 'Below'} "
                f"{sub['threshold']}/100 · "
                f"Current score: {current_score}"
            ):
                s1, s2, s3, s4 = st.columns(4)
                s1.metric(
                    "Threshold",
                    f"{sub['threshold']}/100")
                s2.metric(
                    "Alert type",
                    "Above ↑" if alert_type == "above"
                    else "Below ↓")
                s3.metric(
                    "Current score",
                    f"{current_score}/100")
                s4.metric(
                    "Last alerted",
                    sub.get("last_alerted", "Never"
                            )[:10] if sub.get(
                        "last_alerted") else "Never"
                )
                st.caption(
                    f"Subscribed: "
                    f"{sub.get('created_at', '')[:10]}"
                )

    st.markdown("---")

    # ── How it works ──────────────────────────────────────
    st.subheader("How alerts work")
    st.markdown("""
**1. Subscribe** — Enter your email, choose an observatory
and a threshold score.

**2. Daily check** — Every day at 06:00 UTC, the pipeline
fetches fresh weather data for all 95 observatories.

**3. Comparison** — Your threshold is compared against
the current observation quality score.

**4. Email sent** — If conditions cross your threshold,
you receive a beautifully formatted email with full
weather details and an observing tip.

**Alert types:**
- **Above threshold** — Great for planning. Get notified
  when your favourite site reaches excellent conditions.
- **Below threshold** — Great for operators. Get notified
  when conditions drop, so you know to close the dome.

**Frequency** — Maximum one alert per subscription per day.
    """)
# ═══════════════════════════════════════════════════════
# TAB 11 — Telescope Efficiency
# ═══════════════════════════════════════════════════════
if selected_page == "Telescope Efficiency":
    page_header("🏆", "Telescope Efficiency Score",
        "The single most important number for planning. "
        "Combines weather quality, dark hours, moon position, "
        "seeing, PWV and jet stream into one efficiency score. "
        "Answers: how many truly usable hours will this "
        "telescope produce tonight?")

    # Telescope type selector
    tel_type = st.radio(
        "Telescope type",
        ["Optical", "Infrared", "Radio"],
        horizontal=True,
        help="Different telescope types weight atmospheric "
             "conditions differently"
    )
    tel_type_key = tel_type.lower()

    type_explanations = {
        "Optical":  "Weighted for cloud cover (40%), dark hours (25%), moon (15%), seeing (12%)",
        "Infrared": "Weighted for PWV (25%), cloud cover (30%), dark hours (20%), seeing (8%)",
        "Radio":    "Weighted for PWV (45%), jet stream (20%), cloud cover (20%) — can observe through clouds"
    }
    st.info(f"**{tel_type}:** {type_explanations[tel_type]}")

    with st.spinner(
        f"Calculating {tel_type} telescope efficiency "
        f"for all 95 observatories..."
    ):
        eff_df = load_efficiency_cached(tel_type_key)

    if eff_df.empty:
        st.error("No data available.")
    else:
        # Summary metrics
        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric(
            "Best Site Tonight",
            eff_df.iloc[0]["observatory"].replace(
                " Observatory", "")[:18]
        )
        e2.metric(
            "Top Efficiency Score",
            f"{eff_df.iloc[0]['efficiency_score']}/100"
        )
        e3.metric(
            "Top Grade",
            eff_df.iloc[0]["grade"]
        )
        e4.metric(
            "Max Usable Hours",
            f"{eff_df.iloc[0]['usable_hours']}h"
        )
        e5.metric(
            "A-grade Sites",
            len(eff_df[eff_df["grade"].isin(
                ["A+", "A", "A-"])])
        )

        st.markdown("---")

        # World map coloured by efficiency
        st.subheader(
            f"World map — {tel_type} telescope efficiency")

        m_eff = folium.Map(
            location=[20, 0], zoom_start=2,
            tiles="CartoDB positron"
        )

        for _, row in eff_df.iterrows():
            score = row["efficiency_score"]
            if score >= 80:   color = "#1D9E75"
            elif score >= 65: color = "#378ADD"
            elif score >= 50: color = "#EF9F27"
            else:             color = "#E24B4A"

            popup_html = f"""
                <div style='font-family:sans-serif;
                            width:220px'>
                    <b>{row['observatory']}</b><br>
                    {row['country']} · {row['altitude_m']}m
                    <hr style='margin:4px 0'>
                    <b>Efficiency: {row['efficiency_score']}/100
                    [{row['grade']}]</b><br>
                    Usable hours: {row['usable_hours']}h<br>
                    Dark hours: {row['dark_hours']}h<br>
                    Moon-free: {row['moon_free_pct']}%<br>
                    Weather: {row['weather_score']}/100<br>
                    Seeing: {row['seeing_arcsec']}"<br>
                    PWV: {row['pwv_mm']}mm<br>
                    Jet: {row['jet_impact']}
                </div>
            """
            folium.CircleMarker(
                location=[row["latitude"],
                          row["longitude"]],
                radius=9,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(
                    popup_html, max_width=230),
                tooltip=f"{row['observatory']} — "
                        f"{row['efficiency_score']}/100 "
                        f"[{row['grade']}] · "
                        f"{row['usable_hours']}h usable"
            ).add_to(m_eff)

        st_folium(m_eff, width=None, height=480)

        ec1, ec2, ec3, ec4 = st.columns(4)
        ec1.markdown("🟢 **A grade** — 80+")
        ec2.markdown("🔵 **B grade** — 65–79")
        ec3.markdown("🟡 **C grade** — 50–64")
        ec4.markdown("🔴 **D grade** — below 50")

        st.markdown("---")

        # Rankings
        st.subheader(
            f"Efficiency rankings — {tel_type} telescopes")

        for _, row in eff_df.head(15).iterrows():
            grade = row["grade"]
            if grade in ["A+", "A"]:   emoji = "🟢"
            elif grade == "A-":         emoji = "🟢"
            elif grade in ["B+", "B"]: emoji = "🔵"
            elif grade == "B-":         emoji = "🔵"
            elif grade in ["C+", "C"]: emoji = "🟡"
            else:                       emoji = "🔴"

            with st.expander(
                f"{emoji} **{grade}** — "
                f"{row['observatory']} · "
                f"Efficiency {row['efficiency_score']}/100 · "
                f"{row['usable_hours']}h usable tonight"
            ):
                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Efficiency",
                          f"{row['efficiency_score']}/100")
                r2.metric("Usable Hours",
                          f"{row['usable_hours']}h")
                r3.metric("Dark Hours",
                          f"{row['dark_hours']}h")
                r4.metric("Moon-free",
                          f"{row['moon_free_pct']}%")
                r5.metric("Weather Score",
                          f"{row['weather_score']}/100")

                st.markdown("**Score breakdown**")

                components = row.get("components", {
                   "weather": 0, "dark": 0, "moon": 0,
                   "seeing": 0, "pwv": 0, "jet": 0,
                   "altitude_bonus": 0
              })
                if isinstance(components, str):
                    import json
                    components = json.loads(components)
                comp_cols  = st.columns(
                    len(components))
                labels = {
                    "weather":        "Weather",
                    "dark":           "Dark hours",
                    "moon":           "Moon",
                    "seeing":         "Seeing",
                    "pwv":            "PWV",
                    "jet":            "Jet stream",
                    "altitude_bonus": "Altitude"
                }
                for i, (key, val) in enumerate(
                    components.items()
                ):
                    comp_cols[i].metric(
                        labels.get(key, key),
                        f"+{val}"
                    )

                # Component bar chart
                import matplotlib.pyplot as plt
                import io

                fig, ax = plt.subplots(figsize=(8, 2))
                keys    = list(labels.values())
                vals    = list(components.values())
                colors_comp = [
                    "#1D9E75", "#378ADD", "#AFA9EC",
                    "#5DCAA5", "#85B7EB", "#EF9F27",
                    "#9FE1CB"
                ]
                ax.barh(keys, vals,
                        color=colors_comp[:len(keys)],
                        height=0.6)
                ax.set_xlim(0, 45)
                ax.set_xlabel("Points contributed",
                              fontsize=8, color="white")
                ax.set_facecolor("#0E1117")
                fig.patch.set_facecolor("#0E1117")
                ax.tick_params(colors="white",
                               labelsize=8)
                ax.xaxis.label.set_color("white")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color("#444441")

                buf = io.BytesIO()
                plt.tight_layout()
                plt.savefig(buf, format="png", dpi=120,
                            facecolor="#0E1117",
                            bbox_inches="tight")
                buf.seek(0)
                img_data = buf.getvalue()
                buf.close()   
                st.image(img_data, width='stretch')
                plt.close()

                st.caption(
                    f"{row['country']} · "
                    f"{row['altitude_m']}m · "
                    f"Seeing {row['seeing_arcsec']}\" · "
                    f"PWV {row['pwv_mm']}mm · "
                    f"Jet {row['jet_impact']}"
                )

        st.markdown("---")

        # Full table
        st.subheader("Complete efficiency table")
        eff_display = eff_df[[
            "observatory", "country", "grade",
            "efficiency_score", "usable_hours",
            "dark_hours", "moon_free_pct",
            "weather_score", "seeing_arcsec",
            "pwv_mm", "jet_impact"
        ]].rename(columns={
            "observatory":      "Observatory",
            "country":          "Country",
            "grade":            "Grade",
            "efficiency_score": "Efficiency",
            "usable_hours":     "Usable Hrs",
            "dark_hours":       "Dark Hrs",
            "moon_free_pct":    "Moon-free %",
            "weather_score":    "Weather",
            "seeing_arcsec":    "Seeing (\")",
            "pwv_mm":           "PWV (mm)",
            "jet_impact":       "Jet Impact"
        })
        st.dataframe(
            eff_display, hide_index=True, height=500)

        st.download_button(
            label=f"Download {tel_type} efficiency "
                  f"report as CSV",
            data=eff_display.to_csv(index=False),
            file_name=f"efficiency_{tel_type_key}_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )
        st.markdown("---")

        # ── Cross type comparison ─────────────────────
        st.subheader(
            "🔀 Cross-telescope type comparison")
        st.caption(
            "See how the same observatory ranks "
            "differently for optical, infrared and "
            "radio telescopes. Sites with high rank "
            "spread are highly specialised."
        )

        show_comparison = st.toggle(
            "Show full cross-type comparison "
            "(takes ~30 seconds to calculate)",
            value=False,
            key="cross_compare"
        )

        if show_comparison:
            with st.spinner(
                "Calculating all three telescope "
                "types for all 95 observatories..."
            ):
                from telescope_efficiency import (
                    get_cross_type_comparison)
                cross_df = get_cross_type_comparison()

            if not cross_df.empty:

                # Summary stats
                x1, x2, x3 = st.columns(3)
                best_optical  = cross_df.sort_values(
                    "optical_score",
                    ascending=False).iloc[0]
                best_infrared = cross_df.sort_values(
                    "infrared_score",
                    ascending=False).iloc[0]
                best_radio    = cross_df.sort_values(
                    "radio_score",
                    ascending=False).iloc[0]

                x1.metric(
                    "🔭 Best optical site tonight",
                    best_optical["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_optical['optical_score']}/100"
                )
                x2.metric(
                    "🌡️ Best infrared site tonight",
                    best_infrared["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_infrared['infrared_score']}/100"
                )
                x3.metric(
                    "📡 Best radio site tonight",
                    best_radio["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_radio['radio_score']}/100"
                )

                st.markdown("---")

                # Most specialised sites
                st.subheader(
                    "Most specialised observatories")
                st.caption(
                    "High rank spread means the site "
                    "is dramatically better for one "
                    "telescope type than others."
                )

                specialised = cross_df.sort_values(
                    "rank_spread", ascending=False
                ).head(10)

                for _, row in specialised.iterrows():
                    opt_r  = int(row["optical_rank"])
                    ir_r   = int(row["infrared_rank"])
                    rad_r  = int(row["radio_rank"])
                    spread = int(row["rank_spread"])

                    best   = row["best_type"]
                    emoji  = {
                        "Optical":  "🔭",
                        "Infrared": "🌡️",
                        "Radio":    "📡"
                    }.get(best, "🔭")

                    with st.expander(
                        f"{emoji} **{row['observatory']}** "
                        f"— Best for {best} · "
                        f"Rank spread: {spread} positions"
                    ):
                        c1, c2, c3 = st.columns(3)
                        c1.metric(
                            "🔭 Optical",
                            f"Rank #{opt_r}",
                            f"{row['optical_score']}/100 "
                            f"[{row['optical_grade']}]"
                        )
                        c2.metric(
                            "🌡️ Infrared",
                            f"Rank #{ir_r}",
                            f"{row['infrared_score']}/100 "
                            f"[{row['infrared_grade']}]"
                        )
                        c3.metric(
                            "📡 Radio",
                            f"Rank #{rad_r}",
                            f"{row['radio_score']}/100 "
                            f"[{row['radio_grade']}]"
                        )

                        # Why explanation
                        pwv    = row["pwv_mm"]
                        seeing = row["seeing_arcsec"]
                        jet    = row["jet_impact"]
                        alt    = row["altitude_m"]

                        reasons = []
                        if pwv and pwv < 2:
                            reasons.append(
                                f"very low PWV ({pwv}mm) "
                                f"— excellent for infrared")
                        if pwv and pwv > 10:
                            reasons.append(
                                f"high PWV ({pwv}mm) "
                                f"— poor for infrared/radio")
                        if seeing and seeing < 0.8:
                            reasons.append(
                                f"exceptional seeing "
                                f"({seeing}\") "
                                f"— ideal for optical")
                        if jet in ["Negligible", "Low"]:
                            reasons.append(
                                f"calm jet stream "
                                f"({jet}) "
                                f"— good for radio")
                        if jet in ["High", "Severe"]:
                            reasons.append(
                                f"strong jet stream "
                                f"({jet}) "
                                f"— hurts radio work")
                        if alt > 4000:
                            reasons.append(
                                f"very high altitude "
                                f"({alt}m) — less "
                                f"atmosphere above")

                        if reasons:
                            st.info(
                                "**Why this pattern:** "
                                + " · ".join(reasons))

                        st.caption(
                            f"{row['country']} · "
                            f"{alt}m · "
                            f"Seeing {seeing}\" · "
                            f"PWV {pwv}mm · "
                            f"Jet {jet}"
                        )

                st.markdown("---")

                # Full comparison table
                st.subheader("Full comparison table")
                cross_display = cross_df[[
                    "observatory", "country",
                    "altitude_m",
                    "optical_rank", "optical_score",
                    "optical_grade",
                    "infrared_rank", "infrared_score",
                    "infrared_grade",
                    "radio_rank", "radio_score",
                    "radio_grade",
                    "best_type", "rank_spread",
                    "pwv_mm", "seeing_arcsec",
                    "jet_impact"
                ]].rename(columns={
                    "observatory":     "Observatory",
                    "country":         "Country",
                    "altitude_m":      "Alt (m)",
                    "optical_rank":    "Opt Rank",
                    "optical_score":   "Opt Score",
                    "optical_grade":   "Opt Grade",
                    "infrared_rank":   "IR Rank",
                    "infrared_score":  "IR Score",
                    "infrared_grade":  "IR Grade",
                    "radio_rank":      "Radio Rank",
                    "radio_score":     "Radio Score",
                    "radio_grade":     "Radio Grade",
                    "best_type":       "Best For",
                    "rank_spread":     "Rank Spread",
                    "pwv_mm":          "PWV (mm)",
                    "seeing_arcsec":   "Seeing (\")",
                    "jet_impact":      "Jet Impact"
                })
                st.dataframe(
                    cross_display,
                    hide_index=True,
                    height=500
                )

                st.download_button(
                    label="Download cross-type "
                          "comparison as CSV",
                    data=cross_display.to_csv(
                        index=False),
                    file_name=f"cross_type_comparison_"
                              f"{utcnow().strftime('%Y-%m-%d')}"
                              f".csv",
                    mime="text/csv"
                )
        # ── What makes this different ─────────────────
        st.markdown("---")
        st.subheader("💡 Why efficiency score matters")
        st.markdown(f"""
A site with a perfect **100/100 weather score** but
only **3 dark hours** is less useful than a site with
**85/100 weather** and **10 dark hours**.

The efficiency score captures this by combining:

- **How good the weather is** — cloud, humidity, wind
- **How many hours of darkness are available** tonight
- **How much of the dark time is moon-free**
- **How sharp the images will be** — atmospheric seeing
- **{'PWV for infrared transmission' if tel_type == 'Infrared' else 'Jet stream impact on upper atmosphere' if tel_type == 'Radio' else 'Overall atmospheric stability'}**

The **usable hours** estimate tells you exactly how many
hours of high-quality science you can realistically
expect from each site tonight — the number telescope
schedulers actually care about.
        """)

# ═══════════════════════════════════════════════════════
# TAB 12 — SNR Calculator
# ═══════════════════════════════════════════════════════
if selected_page == "SNR Calculator":
    page_header("📡", "Signal-to-Noise Ratio Calculator",
        "Calculate how detectable your target object will be "
        "tonight at each observatory. Shows full noise budget "
        "breakdown — shot noise, sky background, dark current, "
        "read noise and scintillation. "
        "Accuracy: ~75% for point sources.")

    st.caption("Planning a full observing run? The **Observing Proposal "
               "Planner** solves exposure times for multiple targets and "
               "exports a proposal draft.")

    st.markdown("---")

    # ── Controls ──────────────────────────────────────────
    snr_col1, snr_col2, snr_col3 = st.columns(3)

    with snr_col1:
        # Object selector
        snr_obj_type = st.selectbox(
            "Object type",
            ["All", "Planets", "Messier Objects",
             "NGC Objects", "Famous Stars"],
            key="snr_obj_type"
        )

        # Filter objects that have magnitudes
        if snr_obj_type == "Planets":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k in ["Mercury", "Venus",
                                "Mars", "Jupiter",
                                "Saturn", "Uranus",
                                "Neptune"]]
        elif snr_obj_type == "Messier Objects":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k.startswith("M")]
        elif snr_obj_type == "NGC Objects":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k.startswith("NGC")]
        elif snr_obj_type == "Famous Stars":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if not k.startswith(("M", "N",
                           "Mercury", "Venus", "Mars",
                           "Jupiter", "Saturn",
                           "Uranus", "Neptune"))]
        else:
            obj_keys = list(OBJECT_MAGNITUDES.keys())

        snr_object = st.selectbox(
            "Select target object",
            obj_keys,
            key="snr_object"
        )

        # Photometric filter — universal standard bands, default V.
        snr_filter_name = st.selectbox(
            "Filter / band",
            list(PHOTOMETRIC_FILTERS.keys()),
            index=2,  # V (visual)
            key="snr_filter",
            help="Standard Johnson-Cousins bands plus narrowband "
                 "filters. Narrowband (Hα, OIII) collects far fewer "
                 "photons but isolates emission lines."
        )
        _filt = PHOTOMETRIC_FILTERS[snr_filter_name]
        st.caption(
            f"λ = {_filt['wavelength_nm']} nm · "
            f"bandwidth {_filt['bandwidth_nm']} nm"
        )

    with snr_col2:
        # Custom magnitude option
        use_custom_mag = st.toggle(
            "Use custom magnitude",
            value=False,
            key="custom_mag_toggle"
        )
        if use_custom_mag:
            object_mag = st.number_input(
                "Object magnitude",
                min_value=-5.0,
                max_value=25.0,
                value=float(OBJECT_MAGNITUDES.get(
                    snr_object, 8.0)),
                step=0.1,
                key="custom_mag"
            )
        else:
            object_mag = OBJECT_MAGNITUDES.get(
                snr_object, 8.0)
            st.metric(
                "Object magnitude",
                f"{object_mag} mag"
            )

        # Exposure time
        exposure_preset = st.selectbox(
            "Exposure time",
            ["30 seconds", "1 minute", "5 minutes",
             "10 minutes", "30 minutes", "1 hour",
             "2 hours", "Custom"],
            index=2,
            key="exp_preset"
        )

        preset_map = {
            "30 seconds": 30,
            "1 minute":   60,
            "5 minutes":  300,
            "10 minutes": 600,
            "30 minutes": 1800,
            "1 hour":     3600,
            "2 hours":    7200,
        }

        if exposure_preset == "Custom":
            exposure_s = st.number_input(
                "Custom exposure (seconds)",
                min_value=1,
                max_value=36000,
                value=300,
                key="custom_exp"
            )
        else:
            exposure_s = preset_map[exposure_preset]

    with snr_col3:
        # Moon conditions
        st.markdown("**Moon conditions**")
        moon_phase_input = st.slider(
            "Moon illumination %",
            0, 100, 27,
            key="snr_moon_phase"
        )
        moon_alt_input = st.slider(
            "Moon altitude °",
            -90, 90, 20,
            key="snr_moon_alt"
        )

        sky_brightness = get_sky_brightness(
            moon_phase_input, moon_alt_input)
        st.metric(
            "Sky brightness",
            f"{sky_brightness} mag/arcsec²",
            help="Higher = darker sky = better"
        )

    st.markdown("---")

    # ── Single observatory deep dive ──────────────────────
    st.subheader("Single observatory analysis")

    snr_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="snr_obs"
    )

    obs_row   = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])

    # Get seeing for this observatory
    atm_data = load_atmospheric_cached()
    obs_atm  = atm_data[
        atm_data["observatory"] == snr_obs]
    seeing   = (obs_atm.iloc[0]["seeing_arcsec"]
                if not obs_atm.empty else 1.5)
    pwv      = (obs_atm.iloc[0]["pwv_mm"]
                if not obs_atm.empty else None)

    # Force recalculation when inputs change
    obs_row    = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs  = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])
    atm_data   = load_atmospheric_cached()
    obs_atm    = atm_data[
        atm_data["observatory"] == snr_obs]
    seeing     = (obs_atm.iloc[0]["seeing_arcsec"]
              if not obs_atm.empty else 1.5) or 1.5
    pwv        = (obs_atm.iloc[0]["pwv_mm"]
              if not obs_atm.empty else None)

    # Force fresh calculation every time
    obs_row    = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs  = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])
    atm_data   = load_atmospheric_cached()
    obs_atm    = atm_data[
        atm_data["observatory"] == snr_obs]

    if not obs_atm.empty:
        seeing_val = obs_atm.iloc[0].get("seeing_arcsec")
        pwv_val    = obs_atm.iloc[0].get("pwv_mm")
        seeing     = float(seeing_val) if seeing_val else 1.5
        pwv        = float(pwv_val) if pwv_val else None
    else:
        seeing = 1.5
        pwv    = None

    result = calculate_snr(
        object_magnitude      = float(object_mag),
        exposure_time_s       = int(exposure_s),
        telescope_specs       = tel_specs,
        sky_brightness_mag    = float(sky_brightness),
        seeing_arcsec         = float(seeing),
        object_name           = snr_object,
        object_altitude_deg   = None,
        pwv_mm                = pwv,
        site_altitude_m       = obs_row.get("altitude_m", 2000) or 2000,
        filter_band           = _filt["band"],
        wavelength_nm         = _filt["wavelength_nm"],
        bandwidth_nm          = _filt["bandwidth_nm"],
    )

    # SNR display
    snr_val = result["snr"]
    if snr_val >= 50:   snr_color = "#1D9E75"
    elif snr_val >= 10: snr_color = "#378ADD"
    elif snr_val >= 5:  snr_color = "#EF9F27"
    else:               snr_color = "#E24B4A"

    st.markdown(
        f"<div style='background:{snr_color}22;"
        f"border:1px solid {snr_color};"
        f"border-radius:8px;padding:16px;"
        f"text-align:center;margin:16px 0'>"
        f"<div style='font-size:48px;"
        f"font-weight:bold;color:{snr_color}'>"
        f"SNR = {snr_val}</div>"
        f"<div style='font-size:16px;"
        f"color:{snr_color}'>"
        f"{result['snr_quality']}</div>"
        f"<div style='font-size:12px;color:#888;"
        f"margin-top:4px'>"
        f"{snr_object} · {snr_obs} · "
        f"{exposure_preset if exposure_preset != 'Custom' else f'{exposure_s}s'}"
        f"</div></div>",
        unsafe_allow_html=True
    )

    # Key metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("SNR",           snr_val)
    m2.metric("Limiting mag",
              result["limiting_magnitude"])
    m3.metric("Telescope",
              tel_specs.get("name",
              f"{tel_specs['aperture_m']}m"))
    m4.metric("Seeing",        f"{seeing}\"")
    m5.metric("Sky brightness",
              f"{sky_brightness} mag/arcsec²")

    # Exposure times for SNR targets
    st.markdown("**Time needed to reach SNR targets**")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("SNR = 5  (detection)",
              result["time_for_snr5"])
    t2.metric("SNR = 10 (clear detection)",
              result["time_for_snr10"])
    t3.metric("SNR = 50 (science quality)",
              result["time_for_snr50"])
    t4.metric("SNR = 100 (publication)",
              result["time_for_snr100"])

    # Noise budget chart — Plotly
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    st.markdown("**Noise budget breakdown**")
    budget  = result["noise_budget"]
    sources = list(budget.keys())
    values  = list(budget.values())
    _ncolors = ["#1D9E75","#378ADD","#EF9F27","#E24B4A","#AFA9EC"]
    non_zero = [(s,v) for s,v in zip(sources,values) if v>0]
    _nfig = make_subplots(rows=1, cols=2, subplot_titles=["Noise sources","Noise distribution"], specs=[[{"type":"bar"},{"type":"pie"}]])
    _nfig.add_trace(go.Bar(x=values, y=sources, orientation="h", marker_color=_ncolors[:len(sources)], text=[f"{v:.1f}e⁻" for v in values], textposition="outside", showlegend=False), row=1, col=1)
    if non_zero:
        _nfig.add_trace(go.Pie(labels=[x[0] for x in non_zero], values=[x[1] for x in non_zero], marker_colors=_ncolors[:len(non_zero)], textfont_size=11, hole=0.3), row=1, col=2)
    _nfig.update_layout(
        template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
        paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
        height=360, margin=dict(l=40,r=20,t=60,b=40)
    )
    st.plotly_chart(_nfig, use_container_width=True)

    st.markdown("---")

    # ── Compare across observatories ──────────────────────
    st.subheader(
        "SNR comparison across all observatories")
    st.caption(
        "Which observatory gives the best SNR "
        "for your target tonight?"
    )

    with st.spinner("Calculating SNR for all observatories..."):
        all_snr = cached_snr_all(snr_object, object_mag, exposure_s, moon_phase_input, moon_alt_input)

    if not all_snr.empty:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Best observatory",
                  all_snr.iloc[0]["observatory"].replace(
                      " Observatory", "")[:20])
        s2.metric("Best SNR",
                  all_snr.iloc[0]["snr"])
        s3.metric("Best telescope",
                  all_snr.iloc[0]["telescope"])
        s4.metric("Best aperture",
                  f"{all_snr.iloc[0]['aperture_m']}m")

        st.markdown("**Top 10 observatories by SNR**")
        for _, row in all_snr.head(10).iterrows():
            snr_v = row["snr"]
            if snr_v >= 50:   ec = "#1D9E75"
            elif snr_v >= 10: ec = "#378ADD"
            elif snr_v >= 5:  ec = "#EF9F27"
            else:             ec = "#E24B4A"

            with st.expander(
                f"**{row['observatory']}** — "
                f"SNR {snr_v} · "
                f"{row['snr_quality']} · "
                f"{row['telescope']}"
            ):
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("SNR",       snr_v)
                c2.metric("Aperture",
                          f"{row['aperture_m']}m")
                c3.metric("Limit mag",
                          row["limiting_mag"])
                c4.metric("Time for SNR 10",
                          row["time_snr10"])
                c5.metric("Time for SNR 50",
                          row["time_snr50"])
                st.caption(
                    f"{row['country']} · "
                    f"Seeing {row['seeing']}\" · "
                    f"Sky {row['sky_brightness']} "
                    f"mag/arcsec²"
                )

        # Full table
        st.markdown("**Full SNR table**")
        snr_display = all_snr[[
            "observatory", "country", "telescope",
            "aperture_m", "snr", "snr_quality",
            "limiting_mag", "time_snr5",
            "time_snr10", "time_snr50"
        ]].rename(columns={
            "observatory":  "Observatory",
            "country":      "Country",
            "telescope":    "Telescope",
            "aperture_m":   "Aperture (m)",
            "snr":          "SNR",
            "snr_quality":  "Quality",
            "limiting_mag": "Limit Mag",
            "time_snr5":    "Time SNR=5",
            "time_snr10":   "Time SNR=10",
            "time_snr50":   "Time SNR=50"
        })
        st.dataframe(snr_display,
                     hide_index=True, height=500)

        st.download_button(
            label="Download SNR comparison as CSV",
            data=snr_display.to_csv(index=False),
            file_name=f"snr_{snr_object.replace(' ', '_')}_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )

    st.markdown("---")
    st.caption(
        "⚠️ SNR estimates are approximate (~75% accuracy "
        "for point sources). For precise exposure times "
        "use the official ETC for your telescope. "
        "Extended objects (galaxies, nebulae) may be "
        "overestimated by 2-10x."
    )

# ═══════════════════════════════════════════════════════
# TAB 13 — Live Sky Chart
# ═══════════════════════════════════════════════════════
if _vis_sub == "Live sky chart":
    page_header("🌌", "Live Sky Chart",
        "Real-time sky view for any observatory. "
        "Shows stars, planets, Moon and your target "
        "object. Calculated fresh for the current moment.")

    # Controls
    sky_col1, sky_col2 = st.columns([2, 1])
    with sky_col1:
        sky_obs = st.selectbox(
            "Select observatory",
            df["observatory"].tolist(),
            key="sky_obs"
        )
    with sky_col2:
        show_target = st.toggle(
            "Show target object",
            value=False,
            key="sky_show_target"
        )

    sky_target = None
    if show_target:
        from object_visibility import OBJECTS
        sky_target = st.selectbox(
            "Target object",
            list(OBJECTS.keys()),
            key="sky_target"
        )

    sky_row = df[
        df["observatory"] == sky_obs].iloc[0]

    with st.spinner(
        f"Computing live sky for {sky_obs}..."
    ):
        sky = compute_sky(
            float(sky_row["latitude"]),
            float(sky_row["longitude"]),
            object_name=sky_target
        )

    # ── Sky state banner ──────────────────────────────────
    state_colors = {
        "day":      "#1a3a5c",
        "civil":    "#0d1b2a",
        "twilight": "#050d1a",
        "night":    "#010408"
    }
    state_labels = {
        "day":      "☀️ Daytime — stars not visible",
        "civil":    "🌆 Civil twilight",
        "twilight": "🌃 Astronomical twilight",
        "night":    "🌑 Astronomical night — full dark"
    }
    sky_state = sky["sky_state"]
    # Quick Google Earth link
    gearth_sky = (
        f"https://earth.google.com/web/@"
        f"{sky_row['latitude']},{sky_row['longitude']},"
        f"{sky_row['altitude_m']}a,5000d,35y,0h,0t,0r"
)
    st.caption(
        f"📍 {sky_obs} · "
        f"[Open in Google Earth →]({gearth_sky})"
)
    st.markdown(
        f"<div style='background:{state_colors[sky_state]};"
        f"border-radius:8px;padding:8px 16px;"
        f"margin-bottom:8px;text-align:center;"
        f"color:white;font-weight:bold'>"
        f"{state_labels[sky_state]} · "
        f"Sun altitude: {sky['sun']['altitude']}° · "
        f"Computed: {sky['computed_at']}"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Draw sky chart ────────────────────────────────────
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    import io

    fig = plt.figure(
        figsize=(10, 10),
        facecolor=sky["sky_color"]
    )
    ax  = fig.add_subplot(
        111, projection="polar",
        facecolor=sky["sky_color"]
    )

    # Grid
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.33, 0.67, 1.0])
    ax.set_yticklabels(
        ["Zenith", "60°", "30°", "Horizon"],
        color="#444", fontsize=7
    )
    ax.grid(
        color="#111", alpha=0.3,
        linewidth=0.5, linestyle="--"
    )

    # Cardinal directions
    ax.set_xticks([0, math.pi/2, math.pi, 3*math.pi/2])
    ax.set_xticklabels(
        ["N", "E", "S", "W"],
        color="white", fontsize=14,
        fontweight="bold"
    )

    # Horizon circle
    theta_circle = np.linspace(0, 2*math.pi, 100)
    ax.plot(
        theta_circle,
        [1.0] * 100,
        color="#2a4a2a",
        linewidth=2,
        alpha=0.8
    )

    # ── Constellation lines ───────────────────────────────
    for line in sky["constellation_lines"]:
        ax.plot(
            [line["t1"], line["t2"]],
            [line["r1"], line["r2"]],
            color="#1a3a5c",
            linewidth=0.8,
            alpha=0.6,
            zorder=1
        )

    # ── Stars ─────────────────────────────────────────────
    for star in sky["stars"]:
        if not star["visible"]:
            continue
        color   = "white"
        opacity = star["opacity"]
        size    = star["size"] ** 2

        ax.scatter(
            star["theta"], star["r"],
            s=size,
            c=color,
            alpha=opacity,
            zorder=3,
            edgecolors="none"
        )

        # Label only brightest
        if star["magnitude"] < 1.5:
            ax.annotate(
                star["name"],
                (star["theta"], star["r"]),
                xytext=(5, 5),
                textcoords="offset points",
                color="lightgray",
                fontsize=7,
                zorder=4
            )

    # ── Planets ───────────────────────────────────────────
    for planet in sky["planets"]:
        if not planet["visible"]:
            continue
        ax.scatter(
            planet["theta"], planet["r"],
            s=planet["size"] ** 2,
            c=planet["color"],
            alpha=0.9,
            zorder=5,
            edgecolors="white",
            linewidths=0.5
        )
        ax.annotate(
            planet["name"],
            (planet["theta"], planet["r"]),
            xytext=(6, 6),
            textcoords="offset points",
            color=planet["color"],
            fontsize=8,
            fontweight="bold",
            zorder=6
        )

    # ── Moon ──────────────────────────────────────────────
    moon = sky["moon"]
    if moon["visible"]:
        ax.scatter(
            moon["theta"], moon["r"],
            s=300,
            c="#FFFACD",
            alpha=0.95,
            zorder=7,
            edgecolors="#FFD700",
            linewidths=1
        )
        ax.annotate(
            f"Moon\n{moon['phase']:.0f}%",
            (moon["theta"], moon["r"]),
            xytext=(8, 8),
            textcoords="offset points",
            color="#FFFACD",
            fontsize=8,
            fontweight="bold",
            zorder=8
        )

    # ── Sun ───────────────────────────────────────────────
    sun = sky["sun"]
    if sun["visible"]:
        ax.scatter(
            sun["theta"], sun["r"],
            s=500,
            c="#FFD700",
            alpha=0.95,
            zorder=7,
            edgecolors="#FF8C00",
            linewidths=2
        )
        ax.annotate(
            "Sun",
            (sun["theta"], sun["r"]),
            xytext=(8, 8),
            textcoords="offset points",
            color="#FFD700",
            fontsize=9,
            fontweight="bold",
            zorder=8
        )

    # ── Target object ─────────────────────────────────────
    if sky.get("target"):
        target = sky["target"]
        if target["visible"]:
            ax.scatter(
                target["theta"], target["r"],
                s=400,
                c="none",
                alpha=1.0,
                zorder=9,
                edgecolors="#FF0040",
                linewidths=2,
                marker="o"
            )
            ax.scatter(
                target["theta"], target["r"],
                s=50,
                c="#FF0040",
                alpha=0.9,
                zorder=10
            )
            ax.annotate(
                f"► {target['name']}\n"
                f"Alt: {target['altitude']}°",
                (target["theta"], target["r"]),
                xytext=(10, 10),
                textcoords="offset points",
                color="#FF0040",
                fontsize=9,
                fontweight="bold",
                zorder=11,
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="#000",
                    alpha=0.7,
                    edgecolor="#FF0040"
                )
            )
        else:
            st.warning(
                f"{sky_target} is currently below "
                f"the horizon at {sky_obs}."
            )

    # Title
    ax.set_title(
        f"{sky_obs}\n"
        f"Lat {sky['lat']:.1f}° · "
        f"Lon {sky['lon']:.1f}° · "
        f"{sky['computed_at']}",
        color="white",
        fontsize=10,
        fontweight="bold",
        pad=20
    )

    # Legend
    legend_items = [
        plt.scatter([], [], s=80,
                    c="white", label="Stars"),
        plt.scatter([], [], s=150,
                    c="#FAD5A5",
                    edgecolors="white",
                    label="Planets"),
        plt.scatter([], [], s=200,
                    c="#FFFACD",
                    edgecolors="#FFD700",
                    label="Moon"),
    ]
    if sky.get("target") and sky["target"]["visible"]:
        legend_items.append(
            plt.scatter([], [], s=150,
                        c="none",
                        edgecolors="#FF0040",
                        linewidths=2,
                        label="Target object")
        )
    ax.legend(
        handles=legend_items,
        loc="lower left",
        fontsize=8,
        facecolor="#0A0A1A",
        labelcolor="white",
        framealpha=0.8
    )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(
        buf, format="png", dpi=150,
        facecolor=sky["sky_color"],
        bbox_inches="tight"
    )
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()
    st.image(img_data, width='stretch')
    plt.close()

    # ── Object positions table ────────────────────────────
    st.markdown("---")
    st.subheader("Object positions right now")

    visible_objects = []

    for planet in sky["planets"]:
        visible_objects.append({
            "Object":    planet["name"],
            "Type":      "Planet",
            "Altitude":  f"{planet['altitude']}°",
            "Azimuth":   f"{planet['azimuth']}°",
            "Magnitude": planet["magnitude"],
            "Visible":   "✅" if planet["visible"]
                         else "❌ Below horizon"
        })

    for star in sky["stars"]:
        if star["magnitude"] < 2.0:
            visible_objects.append({
                "Object":    star["name"],
                "Type":      "Star",
                "Altitude":  f"{star['altitude']}°",
                "Azimuth":   f"{star['azimuth']}°",
                "Magnitude": star["magnitude"],
                "Visible":   "✅" if star["visible"]
                             else "❌ Below horizon"
            })

    moon = sky["moon"]
    visible_objects.append({
        "Object":    "Moon",
        "Type":      f"Moon ({moon['phase']:.0f}%)",
        "Altitude":  f"{moon['altitude']}°",
        "Azimuth":   f"{moon['azimuth']}°",
        "Magnitude": -12.7,
        "Visible":   "✅" if moon["visible"]
                     else "❌ Below horizon"
    })

    import pandas as pd
    obj_df = pd.DataFrame(visible_objects)
    st.dataframe(obj_df, hide_index=True, height=400)

    st.caption(
        "Chart updates each time you select a new "
        "observatory. All positions calculated live "
        "using PyEphem for the current UTC time."
    )

# ═══════════════════════════════════════════════════════
# TAB 14 — 7-Day Forecast
# ═══════════════════════════════════════════════════════
# Observatory Detail sub-view selector (rendered here because this
# block precedes the Detail block; choice drives both via the radio).
if selected_page == "Observatory Detail":
    page_header("🔬", "Observatory Detail",
        "Pick an observatory for a complete live analysis, or switch to "
        "its 7-day forecast.")
    _detail_sub = st.radio(
        "View", ["Live detail", "7-day forecast"],
        horizontal=True, key="detail_sub", label_visibility="collapsed")
    st.markdown("---")
else:
    _detail_sub = None

if _detail_sub == "7-day forecast":
    st.subheader("📅 7-Day Observation Forecast")
    st.caption(
        "7-day weather forecast for any observatory. "
        "Shows predicted observation quality scores, "
        "best observing hour each night, cloud cover, "
        "humidity and wind. Updated every hour.")

    fc_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="fc_obs"
    )
    fc_row = df[df["observatory"] == fc_obs].iloc[0]

    gearth_fc = (
        f"https://earth.google.com/web/@"
        f"{fc_row['latitude']},{fc_row['longitude']},"
        f"{fc_row['altitude_m']}a,5000d,35y,0h,0t,0r"
)
    st.caption(
        f"📍 {fc_obs} · "
        f"[Open location in Google Earth →]({gearth_fc})"
)
    fc_row = df[df["observatory"] == fc_obs].iloc[0]

    with st.spinner(f"Fetching 7-day forecast for {fc_obs}..."):
        fc_df, daily_df = cached_forecast(
            float(fc_row["latitude"]), float(fc_row["longitude"]), days=7)

    if daily_df.empty:
        st.error("Could not fetch forecast data.")
    else:
        # ── Meteoblue-style forecast table ────────────────
        def _score_bg(s):
            if s is None: return "#1e2d40", "#5c7a96"
            s = int(s)
            if s >= 80:   return "#0d2e1e", "#1D9E75"
            elif s >= 60: return "#0a1e2e", "#00b4d8"
            elif s >= 40: return "#2e1e0a", "#EF9F27"
            else:         return "#2e0a0a", "#E24B4A"

        def _cloud_icon(cloud):
            if cloud is None: return "—"
            c = int(cloud)
            if c <= 10:  return "☀️"
            elif c <= 30: return "🌤️"
            elif c <= 60: return "⛅"
            elif c <= 85: return "🌥️"
            else:         return "☁️"

        def _precip_icon(prob):
            if prob is None or prob < 20: return ""
            elif prob < 50: return "🌦️"
            else: return "🌧️"

        def _cell(p, show_icon=True):
            if p is None or p.get("score") is None:
                return "<td colspan='1' style='color:#3a4a5a;text-align:center'>—</td>"
            bg, col = _score_bg(p["score"])
            icon = _cloud_icon(p["cloud"])
            rain = _precip_icon(p["precip_prob"])
            wind = int(p["wind"]) if p["wind"] else 0
            temp = p["temp"] if p["temp"] is not None else "—"
            precip = f"{p['precip_mm']}mm" if p.get("precip_mm") and p["precip_mm"] > 0 else ""
            return f"""<td style='background:{bg};border:1px solid #1e2d40;padding:8px 6px;text-align:center;min-width:72px'>
  <div style='font-size:18px;line-height:1'>{icon}{rain}</div>
  <div style='font-size:13px;font-weight:700;color:{col};margin:3px 0'>{int(p['score'])}</div>
  <div style='font-size:10px;color:#5c7a96'>{int(p['cloud'])}% cloud</div>
  <div style='font-size:10px;color:#5c7a96'>{wind} m/s wind</div>
  <div style='font-size:10px;color:#cdd9e5'>{temp}°C</div>
  {'<div style="font-size:10px;color:#00b4d8">' + precip + '</div>' if precip else ''}
</td>"""

        # Build table HTML
        tbl = f"""<div style='overflow-x:auto;border-radius:10px;border:1px solid #1e2d40'>
<table style='border-collapse:collapse;width:100%;font-family:Inter,sans-serif;font-size:12px;background:#0e1117'>
<thead>
<tr style='background:#05070d'>
  <th style='padding:8px 12px;text-align:left;color:#5c7a96;font-size:11px;font-weight:600;letter-spacing:0.08em;border:1px solid #1e2d40;min-width:80px'>PERIOD</th>"""

        for _, row in daily_df.iterrows():
            bg, col = _score_bg(row["night_score"])
            tbl += f"""
  <th colspan='3' style='background:{bg};border:1px solid #1e2d40;padding:8px;text-align:center'>
    <div style='color:{col};font-weight:700;font-size:13px'>{row['day_name'][:3]}</div>
    <div style='color:#cdd9e5;font-size:12px'>{row['date_display']}</div>
    <div style='color:{col};font-size:11px'>{row['condition']}</div>
    <div style='color:#5c7a96;font-size:10px'>{row['min_temp']}° / {row['max_temp']}°C</div>
  </th>"""

        tbl += "</tr>\n<tr style='background:#08090f'>"
        tbl += "<th style='border:1px solid #1e2d40;padding:6px 12px;color:#5c7a96;font-size:10px'></th>"
        for _ in daily_df.iterrows():
            for period in ["AM", "PM", "Night"]:
                tbl += f"<th style='border:1px solid #1e2d40;padding:4px 8px;color:#5c7a96;font-size:10px;text-align:center'>{period}</th>"
        tbl += "</tr></thead><tbody>"

        # Rows
        for label, key, unit in [("Obs. Score", None, ""), ("Cloud %", "cloud", "%"),
                                  ("Humidity %", "humidity", "%"), ("Wind m/s", "wind", " m/s"),
                                  ("Temp °C", "temp", "°C"), ("Precip mm", "precip_mm", " mm"),
                                  ("Precip %", "precip_prob", "%")]:
            tbl += f"<tr><td style='border:1px solid #1e2d40;padding:6px 12px;color:#5c7a96;font-weight:600;font-size:11px;white-space:nowrap;background:#08090f'>{label}</td>"
            for _, row in daily_df.iterrows():
                for period in ["am", "pm", "night"]:
                    p = row[period]
                    if p is None:
                        tbl += "<td style='border:1px solid #1e2d40;text-align:center;color:#3a4a5a'>—</td>"
                        continue
                    if key is None:
                        val = int(p["score"]) if p.get("score") is not None else "—"
                        bg, col = _score_bg(p.get("score"))
                        tbl += f"<td style='background:{bg};border:1px solid #1e2d40;text-align:center;font-weight:700;color:{col}'>{val}</td>"
                    else:
                        val = p.get(key)
                        if val is None:
                            disp = "—"
                        elif key == "temp":
                            disp = f"{val:.1f}{unit}"
                        else:
                            disp = f"{int(val)}{unit}"
                        tbl += f"<td style='border:1px solid #1e2d40;text-align:center;color:#cdd9e5'>{disp}</td>"
            tbl += "</tr>"

        # Weather icon row
        tbl += "<tr><td style='border:1px solid #1e2d40;padding:6px 12px;color:#5c7a96;font-weight:600;font-size:11px;background:#08090f'>Conditions</td>"
        for _, row in daily_df.iterrows():
            for period in ["am", "pm", "night"]:
                p = row[period]
                if p is None:
                    tbl += "<td style='border:1px solid #1e2d40;text-align:center'>—</td>"
                else:
                    icon = _cloud_icon(p.get("cloud"))
                    rain = _precip_icon(p.get("precip_prob"))
                    tbl += f"<td style='border:1px solid #1e2d40;text-align:center;font-size:16px'>{icon}{rain}</td>"
        tbl += "</tr>"

        tbl += "</tbody></table></div>"
        st.markdown(tbl, unsafe_allow_html=True)

        st.markdown("---")

        # ── Score chart (Plotly) ───────────────────────────
        st.subheader("Observation score forecast")
        import plotly.graph_objects as go
        _fc_colors = [("#1D9E75" if s >= 80 else "#00b4d8" if s >= 60 else "#EF9F27" if s >= 40 else "#E24B4A")
                      for s in daily_df["night_score"]]
        _fc_fig = go.Figure(go.Bar(
            x=daily_df["date_display"],
            y=daily_df["night_score"],
            marker_color=_fc_colors,
            text=daily_df["night_score"].astype(int),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Night score: %{y}/100<extra></extra>",
        ))
        _fc_fig.add_hline(y=80, line=dict(color="#1D9E75", dash="dash", width=1), annotation_text="Excellent", annotation_font_color="#1D9E75")
        _fc_fig.add_hline(y=60, line=dict(color="#00b4d8", dash="dash", width=1), annotation_text="Good", annotation_font_color="#00b4d8")
        _fc_fig.update_layout(
            template="plotly_dark", paper_bgcolor=BG2, plot_bgcolor=BG2,
            font=dict(color=TEXT), height=300, margin=dict(l=40,r=20,t=20,b=40),
            yaxis=dict(range=[0,115], title="Night Score"),
            showlegend=False,
        )
        st.plotly_chart(_fc_fig, use_container_width=True)

        st.markdown("---")

        # ── Day by day detail ──────────────────────────────
        st.subheader("Day by day detail")
        for _fc_i, (_, row) in enumerate(daily_df.iterrows()):
            score = row["night_score"]
            if score >= 80:   dot = "🟢"
            elif score >= 60: dot = "🔵"
            elif score >= 40: dot = "🟡"
            else:             dot = "🔴"
            with st.expander(f"{dot} {row['day_name']} {row['date_display']} — Night score: {score}/100 [{row['condition']}] · Best: {row['best_hour']}"):
                d1,d2,d3,d4,d5 = st.columns(5)
                d1.metric("Night Score", f"{row['night_score']}/100")
                d2.metric("Best Hour",   row["best_hour"])
                d3.metric("Avg Cloud",   f"{row['avg_cloud']}%")
                d4.metric("Avg Humidity",f"{row['avg_humidity']}%")
                d5.metric("Avg Wind",    f"{row['avg_wind']} m/s")
                t1,t2,t3 = st.columns(3)
                t1.metric("Min Temp",  f"{row['min_temp']}°C")
                t2.metric("Max Temp",  f"{row['max_temp']}°C")
                t3.metric("Rain Prob", f"{row['precip_prob']}%")

                hourly = row["hourly_scores"]
                if hourly:
                    _hfig = go.Figure(go.Bar(
                        x=[h["hour"] for h in hourly],
                        y=[h["score"] for h in hourly],
                        marker_color=[("#1D9E75" if h["score"]>=80 else "#00b4d8" if h["score"]>=60 else "#EF9F27" if h["score"]>=40 else "#E24B4A") for h in hourly],
                        hovertemplate="%{x}:00 UTC<br>Score: %{y:.0f}/100<extra></extra>",
                    ))
                    _hfig.update_layout(
                        template="plotly_dark", paper_bgcolor=BG3, plot_bgcolor=BG3,
                        font=dict(color=TEXT, size=10), height=160,
                        margin=dict(l=30,r=10,t=10,b=30),
                        xaxis=dict(tickmode="linear", dtick=3, title="Hour UTC"),
                        yaxis=dict(range=[0,105], title="Score"),
                        showlegend=False,
                    )
                    st.plotly_chart(_hfig, use_container_width=True,
                                    key=f"fc_hourly_{_fc_i}")

        st.markdown("---")


        st.markdown("---")

        # ── Full forecast table ────────────────────────────
        st.subheader("Full forecast table")
        fc_display = daily_df[[
            "date", "day_name", "night_score",
            "condition", "best_hour", "best_score",
            "avg_cloud", "avg_humidity", "avg_wind",
            "min_temp", "max_temp", "precip_prob"
        ]].rename(columns={
            "date":         "Date",
            "day_name":     "Day",
            "night_score":  "Night Score",
            "condition":    "Condition",
            "best_hour":    "Best Hour",
            "best_score":   "Best Score",
            "avg_cloud":    "Cloud %",
            "avg_humidity": "Humidity %",
            "avg_wind":     "Wind m/s",
            "min_temp":     "Min °C",
            "max_temp":     "Max °C",
            "precip_prob":  "Rain Prob %"
        })
        st.dataframe(fc_display,
                     hide_index=True, height=300)

        st.download_button(
            label="Download forecast as CSV",
            data=fc_display.to_csv(index=False),
            file_name=f"forecast_{fc_obs.replace(' ', '_')}_"
                      f"{utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        st.caption(
            "Forecast data from Open-Meteo · "
            "Free, open-source weather API · "
            "Night scores based on 18:00-06:00 UTC hours · "
            "Updated hourly"
        )

# ═══════════════════════════════════════════════════════
# SKY EVENTS — one tab, internal selector for the 5 trackers
# ═══════════════════════════════════════════════════════
if selected_page == "Sky Events":
    page_header("🌠", "Sky Events",
        "Live trackers for comets, asteroids, satellites, meteor showers "
        "and eclipses — and which observatories have the best view.")
    _sky_sub = st.radio(
        "Event type",
        ["Comet Tracker", "Asteroid Tracker", "Satellite Passes",
         "Meteor Showers", "Eclipses & Transits"],
        horizontal=True, key="sky_sub", label_visibility="collapsed")
    st.markdown("---")
else:
    _sky_sub = None

# ═══════════════════════════════════════════════════════
# Comet Tracker (within Sky Events)
# ═══════════════════════════════════════════════════════
if _sky_sub == "Comet Tracker":
    page_header("☄️", "Comet Tracker",
        "Track currently observable comets worldwide. "
        "Shows real-time visibility from your selected "
        "observatory, brightness, and which telescope "
        "is needed to see each comet tonight.")

    comets = cached_comets()

    # Summary metrics
    trackable = [c for c in comets
                 if c.get("ra_deg") is not None]
    naked_eye = [c for c in comets
                 if c.get("magnitude", 99) < 6
                 and c.get("ra_deg") is not None]
    bino      = [c for c in comets
                 if 6 <= c.get("magnitude", 99) < 10
                 and c.get("ra_deg") is not None]

    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.metric("Total Comets",      len(comets))
    cm2.metric("Trackable Tonight", len(trackable))
    cm3.metric("Naked Eye",         len(naked_eye))
    cm4.metric("Binoculars",        len(bino))

    st.markdown("---")

    # Observatory selector
    comet_obs = st.selectbox(
        "Select observatory for visibility",
        df["observatory"].tolist(),
        key="comet_obs"
    )
    comet_row = df[
        df["observatory"] == comet_obs].iloc[0]
    clat = float(comet_row["latitude"])
    clon = float(comet_row["longitude"])

    st.markdown("---")

    # Display each comet
    st.subheader(
        f"Comet visibility from {comet_obs}")

    for comet in comets:
        mag     = comet.get("magnitude", 99)
        status  = comet.get("status", "Unknown")

        if "🟢" in status:   status_emoji = "🟢"
        elif "🟡" in status: status_emoji = "🟡"
        elif "🔴" in status: status_emoji = "🔴"
        else:                status_emoji = "⚪"

        # Get visibility
        vis = get_comet_visibility(
            comet, clat, clon)

        vis_str = ""
        if vis:
            if vis["visible"]:
                vis_str = (f"🔭 Visible — "
                           f"Alt {vis['altitude']}°")
            else:
                vis_str = (f"❌ Below horizon — "
                           f"Alt {vis['altitude']}°")
        else:
            vis_str = "📍 No position data"

        with st.expander(
            f"{status_emoji} **{comet['name']}** — "
            f"Magnitude {mag} · "
            f"{magnitude_to_visibility(mag)} · "
            f"{vis_str}"
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Magnitude",   mag)
            c2.metric("Type",        comet["type"])
            c3.metric("Perihelion",
                      comet.get("perihelion", "N/A"))
            c4.metric("Discovered",
                      str(comet.get(
                          "discovery_year", "N/A")))

            if vis:
                v1, v2, v3, v4 = st.columns(4)
                v1.metric("Altitude",
                          f"{vis['altitude']}°")
                v2.metric("Azimuth",
                          f"{vis['azimuth']}°")
                v3.metric("Rises",
                          vis.get("rise_time", "N/A"))
                v4.metric("Sets",
                          vis.get("set_time", "N/A"))

            st.info(
                f"**{comet['name']}** — "
                f"{comet.get('notes', '')} · "
                f"Discovered by "
                f"{comet.get('discoverer', 'Unknown')} · "
                f"Type: {comet_type_info(comet['type'])}"
            )

            if comet.get("period_yr"):
                st.caption(
                    f"Orbital period: "
                    f"{comet['period_yr']} years"
                )

    st.markdown("---")

    # World map showing which observatories
    # can see comets tonight
    st.subheader(
        "World map — comet visibility tonight")
    st.caption(
        "Green markers can see at least one comet "
        "above 10° altitude right now."
    )

    import folium
    m_comet = folium.Map(
        location=[20, 0], zoom_start=2,
        tiles="CartoDB positron"
    )

    # Sample every 5th observatory for speed
    sample_df = df.iloc[:5]

    for _, obs_row in sample_df.iterrows():
        lat = float(obs_row["latitude"])
        lon = float(obs_row["longitude"])

        visible_comets = []
        for comet in trackable:
            vis = get_comet_visibility(
                comet, lat, lon)
            if vis and vis["visible"]:
                visible_comets.append(
                    comet["name"])

        color   = "#1D9E75" if visible_comets else "#444441"
        tooltip = (
            f"{obs_row['observatory']} — "
            f"{len(visible_comets)} comets visible"
            if visible_comets
            else f"{obs_row['observatory']} — no comets"
        )
        popup = (
            f"<b>{obs_row['observatory']}</b><br>"
            f"Visible comets:<br>" +
            "<br>".join(visible_comets)
            if visible_comets
            else f"<b>{obs_row['observatory']}</b><br>"
                 f"No comets above horizon"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=tooltip,
            popup=folium.Popup(popup, max_width=200)
        ).add_to(m_comet)

    st_folium(m_comet, width=None, height=400)

    st.markdown("---")

    # Educational section
    st.subheader("🎓 About comets")
    st.markdown("""
**What is a comet?**
A comet is an icy body from the outer solar system.
When it approaches the Sun, heat vaporises the ice
creating a glowing coma and tail that can stretch
millions of kilometres.

**Types of comets:**
- **Short-period** — orbit the Sun in under 200 years.
  Predictable and well-studied. Example: Halley's Comet.
- **Long-period** — take thousands of years per orbit.
  Often first-time visitors from the Oort Cloud.
- **Interstellar** — from outside our solar system entirely.
  Only 3 confirmed: 1I/Oumuamua, 2I/Borisov, 3I/ATLAS.
- **Sungrazers** — pass extremely close to the Sun.
  Often spectacular but frequently break apart.

**Why are comets unpredictable?**
Comets are nicknamed "dirty snowballs". As they heat up
they outgas jets of material that can change their
brightness dramatically. A comet predicted at magnitude 8
can brighten to magnitude 1 — or completely disintegrate.

**How to observe:**
- Start with binoculars — sweep slowly across the
  predicted position
- Look for a fuzzy patch that does not look like a star
- The tail always points away from the Sun
- Best viewing is away from city lights
    """)

    st.caption(
        "Comet positions are approximate. "
        "For precise ephemeris data visit "
        "minorplanetcenter.net or heavens-above.com"
    )

# ═══════════════════════════════════════════════════════
# TAB 16 — Observatory Reviews
# ═══════════════════════════════════════════════════════
if selected_page == "Observatory Reviews":
    page_header("⭐", "Observatory Reviews & Ratings",
        "Share your experience visiting observatories "
        "worldwide. Rate seeing conditions, darkness, "
        "and accessibility. Help other astronomers "
        "plan their visits.")

    # ── Summary metrics ───────────────────────────────────
    top_rated, recent = cached_top_reviews()

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Total Reviews",
              len(recent) if not recent.empty else 0)
    r2.metric("Observatories Reviewed",
              len(top_rated) if not top_rated.empty else 0)
    if not top_rated.empty:
        r3.metric("Highest Rated",
                  top_rated.iloc[0]["observatory"]
                  .replace(" Observatory", "")[:20])
        r4.metric("Top Rating",
                  f"{top_rated.iloc[0]['avg_rating']}/5")
    else:
        r3.metric("Highest Rated", "No reviews yet")
        r4.metric("Top Rating",    "—")

    st.markdown("---")

    # ── Tabs within tab ───────────────────────────────────
    rev_tab1, rev_tab2, rev_tab3 = st.tabs([
        "📝 Write a Review",
        "🔍 Browse Reviews",
        "🏆 Top Rated"
    ])

    # ── Write a review ────────────────────────────────────
    with rev_tab1:
        st.subheader("Share your experience")

        with st.form("review_form"):
            # Observatory selector
            rev_obs = st.selectbox(
                "Observatory visited",
                df["observatory"].tolist(),
                key="rev_obs"
            )

            # Reviewer name
            rev_name = st.text_input(
                "Your name or username",
                placeholder="e.g. AstroEnthusiast99"
            )

            # Overall rating
            st.markdown("**Overall rating**")
            rev_rating = st.slider(
                "Overall rating",
                min_value=1,
                max_value=5,
                value=4,
                key="rev_rating"
            )
            st.markdown(stars(rev_rating))

            # Sub-ratings
            st.markdown("**Detailed ratings**")
            sub1, sub2, sub3 = st.columns(3)
            with sub1:
                seeing_r = st.slider(
                    "Seeing conditions",
                    1, 5, 4,
                    key="seeing_r",
                    help="1 = very poor, 5 = exceptional"
                )
                st.caption(stars(seeing_r))
            with sub2:
                dark_r = st.slider(
                    "Sky darkness",
                    1, 5, 4,
                    key="dark_r",
                    help="1 = heavily light polluted, 5 = pristine dark sky"
                )
                st.caption(stars(dark_r))
            with sub3:
                access_r = st.slider(
                    "Accessibility",
                    1, 5, 3,
                    key="access_r",
                    help="1 = very difficult to reach, 5 = easy access"
                )
                st.caption(stars(access_r))

            # Visit details
            st.markdown("**Visit details**")
            d1, d2 = st.columns(2)
            with d1:
                visit_date = st.date_input(
                    "Date of visit",
                    key="visit_date"
                )
            with d2:
                telescope = st.text_input(
                    "Telescope used",
                    placeholder="e.g. 10-inch Dobsonian"
                )

            objects = st.text_input(
                "Objects observed",
                placeholder="e.g. M42, Jupiter, Andromeda Galaxy"
            )

            # Review text
            review_text = st.text_area(
                "Your review",
                placeholder=(
                    "Describe your experience — "
                    "seeing conditions, what you observed, "
                    "tips for other visitors..."
                ),
                height=150
            )

            submitted = st.form_submit_button(
                "Submit Review",
                type="primary"
            )

            if submitted:
                if not rev_name:
                    st.error(
                        "Please enter your name.")
                elif not review_text:
                    st.error(
                        "Please write a review.")
                else:
                    success, msg = add_review(
                        observatory      = rev_obs,
                        reviewer_name    = rev_name,
                        rating           = rev_rating,
                        review_text      = review_text,
                        visit_date       = str(
                            visit_date),
                        telescope_used   = telescope,
                        objects_observed = objects,
                        seeing_rating    = seeing_r,
                        darkness_rating  = dark_r,
                        access_rating    = access_r
                    )
                    if success:
                        st.success(
                            f"✅ Thank you {rev_name}! "
                            f"Your review of {rev_obs} "
                            f"has been submitted."
                        )
                        st.balloons()
                    else:
                        st.error(msg)

    # ── Browse reviews ────────────────────────────────────
    with rev_tab2:
        st.subheader("Browse observatory reviews")

        browse_obs = st.selectbox(
            "Select observatory",
            ["All observatories"] +
            df["observatory"].tolist(),
            key="browse_obs"
        )

        if browse_obs == "All observatories":
            _, reviews_df_all = cached_top_reviews()
            reviews_df = reviews_df_all.head(50) if not reviews_df_all.empty else reviews_df_all
            stats      = None
        else:
            reviews_df, stats = cached_reviews(browse_obs)

        # Show stats for selected observatory
        if stats and stats["total_reviews"]:
            st.markdown("---")
            st.subheader(
                f"Stats for {browse_obs}")

            color = rating_color(stats["avg_rating"])
            st.markdown(
                f"<div style='background:{color}22;"
                f"border:2px solid {color};"
                f"border-radius:8px;"
                f"padding:16px;margin-bottom:16px'>"
                f"<div style='font-size:36px;"
                f"font-weight:bold;color:{color}'>"
                f"{'⭐' * int(round(float(stats['avg_rating'])))}"
                f"</div>"
                f"<div style='font-size:24px;"
                f"color:{color};font-weight:bold'>"
                f"{stats['avg_rating']} / 5</div>"
                f"<div style='color:#888;font-size:13px'>"
                f"Based on {stats['total_reviews']} "
                f"{'review' if stats['total_reviews'] == 1 else 'reviews'}"
                f"</div></div>",
                unsafe_allow_html=True
            )

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Reviews",
                      stats["total_reviews"])
            s2.metric("Avg Seeing",
                      f"{stats['avg_seeing']}/5"
                      if stats["avg_seeing"] else "N/A")
            s3.metric("Avg Darkness",
                      f"{stats['avg_darkness']}/5"
                      if stats["avg_darkness"] else "N/A")
            s4.metric("Avg Access",
                      f"{stats['avg_access']}/5"
                      if stats["avg_access"] else "N/A")

            # Rating distribution chart
            dist = get_rating_distribution(browse_obs)
            if not dist.empty:
                import matplotlib.pyplot as plt
                import io

                fig, ax = plt.subplots(figsize=(6, 2))
                all_ratings = {1: 0, 2: 0,
                               3: 0, 4: 0, 5: 0}
                for _, row in dist.iterrows():
                    all_ratings[row["rating"]] = \
                        row["count"]

                rating_labels = [
                    f"{'⭐' * r}" for r in range(5, 0, -1)]
                rating_vals   = [
                    all_ratings[r]
                    for r in range(5, 0, -1)]
                bar_colors    = [
                    "#1D9E75", "#378ADD",
                    "#EF9F27", "#E24B4A", "#888"
                ]

                ax.barh(
                    rating_labels,
                    rating_vals,
                    color=bar_colors,
                    height=0.6
                )
                for i, val in enumerate(rating_vals):
                    if val > 0:
                        ax.text(
                            val + 0.05, i,
                            str(val),
                            va="center",
                            color="white",
                            fontsize=9
                        )
                ax.set_xlabel(
                    "Number of reviews",
                    color="white", fontsize=8)
                ax.set_facecolor("#0E1117")
                fig.patch.set_facecolor("#0E1117")
                ax.tick_params(
                    colors="white", labelsize=9)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color(
                    "#444441")

                buf = io.BytesIO()
                plt.tight_layout()
                plt.savefig(
                    buf, format="png", dpi=120,
                    facecolor="#0E1117",
                    bbox_inches="tight"
                )
                buf.seek(0)
                img_data = buf.getvalue()
                buf.close()
                st.image(img_data, width="stretch")
                plt.close()

        st.markdown("---")

        # Display reviews
        if reviews_df is None or reviews_df.empty:
            st.info(
                "No reviews yet for this observatory. "
                "Be the first to leave a review!"
            )
        else:
            st.subheader(
                f"{len(reviews_df)} "
                f"{'review' if len(reviews_df) == 1 else 'reviews'}"
            )

            for _, rev in reviews_df.iterrows():
                rating    = rev.get("rating", 0)
                color     = rating_color(rating)
                name      = rev.get(
                    "reviewer_name", "Anonymous")
                date      = str(rev.get(
                    "created_at", ""))[:10]
                visit     = rev.get(
                    "visit_date", "")
                telescope = rev.get(
                    "telescope_used", "")
                objects   = rev.get(
                    "objects_observed", "")
                text      = rev.get(
                    "review_text", "")

                # Show observatory name if browsing all
                obs_header = ""
                if browse_obs == "All observatories":
                    obs_header = (
                        f"**{rev.get('observatory', '')}**"
                        f" · "
                    )

                with st.expander(
                    f"{'⭐' * int(rating)} "
                    f"{obs_header}"
                    f"**{name}** · "
                    f"{'Visited ' + str(visit) if visit else ''} "
                    f"· Reviewed {date}"
                ):
                    st.markdown(
                        f"<div style='background:{color}11;"
                        f"border-left:3px solid {color};"
                        f"padding:12px;border-radius:4px;"
                        f"margin-bottom:8px'>"
                        f"{text}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    if telescope or objects:
                        d1, d2 = st.columns(2)
                        if telescope:
                            d1.caption(
                                f"🔭 {telescope}")
                        if objects:
                            d2.caption(
                                f"🌌 {objects}")

                    sr = rev.get("seeing_rating")
                    dr = rev.get("darkness_rating")
                    ar = rev.get("access_rating")

                    if any([sr, dr, ar]):
                        sub1, sub2, sub3 = st.columns(3)
                        if sr:
                            sub1.metric(
                                "Seeing",
                                f"{'⭐' * int(sr)}")
                        if dr:
                            sub2.metric(
                                "Darkness",
                                f"{'⭐' * int(dr)}")
                        if ar:
                            sub3.metric(
                                "Access",
                                f"{'⭐' * int(ar)}")

    # ── Top rated ─────────────────────────────────────────
    with rev_tab3:
        st.subheader("🏆 Top rated observatories")
        st.caption(
            "Ranked by average visitor rating. "
            "Based on real reviews from astronomers "
            "who have visited these sites."
        )

        if top_rated.empty:
            st.info(
                "No reviews yet. Be the first to "
                "review an observatory!"
            )
        else:
            for i, (_, row) in enumerate(
                top_rated.iterrows()
            ):
                color  = rating_color(row["avg_rating"])
                medal  = (
                    "🥇" if i == 0
                    else "🥈" if i == 1
                    else "🥉" if i == 2
                    else f"#{i+1}"
                )

                with st.expander(
                    f"{medal} **{row['observatory']}** "
                    f"— {'⭐' * int(round(float(row['avg_rating'])))} "
                    f"({row['avg_rating']}/5) · "
                    f"{row['total_reviews']} "
                    f"{'review' if row['total_reviews'] == 1 else 'reviews'}"
                ):
                    t1, t2, t3, t4 = st.columns(4)
                    t1.metric("Overall",
                              f"{row['avg_rating']}/5")
                    t2.metric("Seeing",
                              f"{row['avg_seeing']}/5"
                              if row["avg_seeing"]
                              else "N/A")
                    t3.metric("Darkness",
                              f"{row['avg_darkness']}/5"
                              if row["avg_darkness"]
                              else "N/A")
                    t4.metric("Access",
                              f"{row['avg_access']}/5"
                              if row["avg_access"]
                              else "N/A")

                    if row.get("latest_visit"):
                        st.caption(
                            f"Latest visit: "
                            f"{row['latest_visit']}"
                        )

                    # Show latest review for this obs
                    latest, _ = cached_reviews(row["observatory"])
                    if not latest.empty:
                        rev = latest.iloc[0]
                        st.markdown(
                            f"*\"{rev['review_text']}\"*"
                        )
                        st.caption(
                            f"— {rev['reviewer_name']}"
                        )

        st.markdown("---")

        # Full table
        if not top_rated.empty:
            st.subheader("Full ratings table")
            top_display = top_rated[[
                "observatory", "total_reviews",
                "avg_rating", "avg_seeing",
                "avg_darkness", "avg_access"
            ]].rename(columns={
                "observatory":    "Observatory",
                "total_reviews":  "Reviews",
                "avg_rating":     "Overall",
                "avg_seeing":     "Seeing",
                "avg_darkness":   "Darkness",
                "avg_access":     "Access"
            })
            st.dataframe(
                top_display,
                hide_index=True,
                height=400
            )

            st.download_button(
                label="Download ratings as CSV",
                data=top_display.to_csv(index=False),
                file_name=f"observatory_ratings_"
                          f"{utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )


# ═══════════════════════════════════════════════════════
# Feedback & Suggestions
# ═══════════════════════════════════════════════════════
if selected_page == "Feedback & Suggestions":
    page_header("💬", "Feedback & Suggestions",
        "Found a bug, want a feature, or have an idea? Tell us — this "
        "platform is shaped by what observers actually need.")

    # ── Recently added changelog ───────────────────────
    st.subheader("Recently added")
    st.markdown("""
- **Observing Proposal Planner** — build a full proposal with SNR-solved exposures
- **Genuine observing-quality score** — multiplicative index (cloud, seeing, moon, precip)
- **Fried-parameter seeing** & altitude-calibrated extinction (matches published values)
- **SNR-driven Peak Observing Time** and airmass-enriched Object Visibility
- **Filter/band selector** (V/B/R/I/Hα/OIII) in the SNR calculator
- Consolidated navigation into 16 focused tabs
""")

    st.markdown("---")

    # ── Feedback form ──────────────────────────────────
    st.subheader("Send feedback")
    from feedback import add_feedback, get_feedback
    with st.form("feedback_form"):
        fb_category = st.selectbox("Type",
            ["Feature request", "Bug report", "General feedback",
             "Data / accuracy issue"], key="fb_cat")
        fb_message = st.text_area("Your message",
            placeholder="Describe the idea, problem, or feedback…",
            height=140, key="fb_msg")
        fb_contact = st.text_input("Email (optional, for follow-up)",
            placeholder="you@example.com", key="fb_contact")
        fb_submit = st.form_submit_button("Submit feedback", type="primary")

        if fb_submit:
            if not fb_message or len(fb_message.strip()) < 5:
                st.error("Please enter a bit more detail.")
            else:
                ok, msg = add_feedback(fb_category, fb_message.strip(),
                                       fb_contact.strip())
                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)

    # ── Owner-only recent feedback (via ?admin=1) ──────
    if st.query_params.get("admin") == "1":
        st.markdown("---")
        st.subheader("Recent feedback (admin)")
        _fb_df = get_feedback(100)
        if _fb_df.empty:
            st.caption("No feedback yet.")
        else:
            st.dataframe(_fb_df, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════
# TAB 17 — Satellite Pass Predictor
# ═══════════════════════════════════════════════════════
if _sky_sub == "Satellite Passes":
    page_header("🛸", "Satellite Pass Predictor",
        "Predict when the ISS and other spacecraft pass "
        "over your selected observatory. Shows visible "
        "passes, brightness, direction and duration. "
        "All times in UTC.")

    # ── Controls ──────────────────────────────────────────
    sat_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="sat_obs"
    )
    sat_row = df[df["observatory"] == sat_obs].iloc[0]
    sat_lat = float(sat_row["latitude"])
    sat_lon = float(sat_row["longitude"])
    sat_alt = float(sat_row["altitude_m"] or 0)

    hours_ahead = st.slider(
        "Hours to look ahead",
        min_value=6, max_value=48,
        value=24, step=6, key="sat_hours"
    )

    # ── Button to trigger calculation ─────────────────────
    if st.button(
        "🛸 Calculate Satellite Passes",
        type="primary",
        key="calc_passes_btn"
    ):
        with st.spinner(
            f"Fetching TLE data and calculating "
            f"passes for {sat_obs}..."
        ):
            sat_results = get_all_passes(
                sat_lat, sat_lon, sat_alt,
                hours_ahead=hours_ahead
            )
        st.session_state["sat_results"]     = sat_results
        st.session_state["sat_results_obs"] = sat_obs
    # ── Load from session state ───────────────────────────
    sat_results = st.session_state.get("sat_results", {})

    if not sat_results:
        st.info(
            "Select an observatory and click "
            "**Calculate Satellite Passes** to see "
            "when the ISS and other spacecraft pass "
            "overhead. Calculation takes about "
            "10-15 seconds."
        )
        st.markdown("---")
        st.subheader("🎓 About satellite passes")
        st.markdown("""
**Why can I see the ISS?**
The ISS is large — roughly the size of a football
pitch — and covered in solar panels that reflect
sunlight. When it passes overhead during twilight
or night while sunlit, it appears as a fast-moving
bright dot crossing the sky in about 6 minutes.

**When is the best time to look?**
The ISS is only visible when it is in sunlight but
you are in darkness — typically 30 to 90 minutes
after sunset or before sunrise. Passes marked
✅ VISIBLE meet this condition.

**How bright does it get?**
At its brightest the ISS reaches magnitude -5 —
brighter than Venus and visible even in twilight.
Average passes are magnitude -1 to -3.

**How fast does it move?**
The ISS travels at 7.66 km/s — completing one orbit
every 92 minutes. A typical pass lasts 4 to 7 minutes
from horizon to horizon.
        """)
        st.caption(
            "Pass predictions use PyEphem with TLE data "
            "from Celestrak. Times are in UTC. "
            "For precise predictions visit "
            "heavens-above.com or n2yo.com"
        )

    else:
        # Show which observatory results are for
        cached_obs = st.session_state.get(
            "sat_results_obs", sat_obs)
        if cached_obs != sat_obs:
            st.warning(
                f"Showing results for **{cached_obs}**. "
                f"Click Calculate to update for "
                f"**{sat_obs}**."
            )

        # ── Summary metrics ───────────────────────────────
        total_passes   = sum(
            len(s["passes"])
            for s in sat_results.values())
        visible_passes = sum(
            1 for s in sat_results.values()
            for p in s["passes"]
            if p["is_visible"])
        bright_passes  = sum(
            1 for s in sat_results.values()
            for p in s["passes"]
            if p["is_visible"] and p["magnitude"] < 0)

        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Total Passes",    total_passes)
        sm2.metric("Visible Tonight", visible_passes)
        sm3.metric("Bright Passes",   bright_passes)
        sm4.metric("Satellites",      len(sat_results))

        st.markdown("---")

        # ── ISS current position ──────────────────────────
        st.subheader("🛸 ISS — Current Position")
        iss_data = sat_results.get("ISS", {})
        iss_pos  = iss_data.get("position")

        if iss_pos:
            ip1, ip2, ip3, ip4 = st.columns(4)
            ip1.metric(
                "Altitude",
                f"{iss_pos['altitude']}°",
                "Above horizon" if iss_pos["visible"]
                else "Below horizon"
            )
            ip2.metric(
                "Azimuth",
                f"{iss_pos['azimuth']}° "
                f"({iss_pos['direction']})"
            )
            ip3.metric(
                "Range",
                f"{iss_pos['range_km']:,} km"
            )
            ip4.metric(
                "Currently",
                "🌟 Overhead!" if iss_pos["visible"]
                else "🌍 Below horizon"
            )
            if iss_pos.get("sublat") is not None:
                st.caption(
                    f"ISS ground track: "
                    f"{iss_pos['sublat']}°N, "
                    f"{iss_pos['sublong']}°E · "
                    f"[Track live →]"
                    f"(https://www.n2yo.com/?s=25544)"
                )

        st.markdown("---")

        # ── Pass predictions ──────────────────────────────
        for sat_key, sat_data in sat_results.items():
            passes   = sat_data["passes"]
            sat_name = sat_data["name"]
            icon     = sat_data.get("icon", "🛰️")

            if not passes:
                continue

            visible = [p for p in passes
                       if p["is_visible"]]
            st.subheader(
                f"{icon} {sat_name} — "
                f"{len(passes)} passes · "
                f"{len(visible)} visible"
            )

            for p in passes:
                if p["is_visible"]:
                    status_emoji = "✅"
                    status_text  = "VISIBLE"
                elif p["is_night"]:
                    status_emoji = "🌙"
                    status_text  = "Night — in shadow"
                else:
                    status_emoji = "☀️"
                    status_text  = "Daytime"

                with st.expander(
                    f"{status_emoji} "
                    f"{p['day_name']} "
                    f"{p['rise_time']} → "
                    f"{p['set_time']} · "
                    f"Max {p['max_alt']}° · "
                    f"Mag {p['magnitude']} "
                    f"{p['mag_emoji']} · "
                    f"{p['rise_dir']} → {p['set_dir']}"
                    f" · {status_text}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Rise Time",
                              p["rise_time"])
                    c2.metric("Max Altitude",
                              f"{p['max_alt']}°")
                    c3.metric("Set Time",
                              p["set_time"])
                    c4.metric("Duration",
                              p["duration_str"])
                    c5.metric("Brightness",
                              f"Mag {p['magnitude']}")

                    d1, d2, d3 = st.columns(3)
                    d1.metric("Rises in",
                              p["rise_dir"])
                    d2.metric("Sets in",
                              p["set_dir"])
                    d3.metric("Sun altitude",
                              f"{p['sun_alt']}°")

                    st.info(
                        f"**{p['mag_emoji']} "
                        f"{p['mag_desc']}** — "
                        f"Look {p['rise_dir']} at "
                        f"{p['rise_time']} and track "
                        f"to {p['set_dir']}. "
                        f"Peak altitude {p['max_alt']}° "
                        f"at {p['max_time']}. "
                        f"Duration: {p['duration_str']}."
                    )

                    if p["is_visible"]:
                        st.success(
                            f"✅ **Visible pass** — "
                            f"Set an alarm for "
                            f"{p['rise_time']}!"
                        )

            st.markdown("---")

        # ── Visible passes summary table ──────────────────
        st.subheader("📅 Visible passes summary")

        all_visible = []
        for sat_key, sat_data in sat_results.items():
            for p in sat_data["passes"]:
                if p["is_visible"]:
                    all_visible.append({
                        "Satellite":  sat_data["name"],
                        "Date":       p["date_str"],
                        "Day":        p["day_name"],
                        "Rise":       p["rise_time"],
                        "Max Alt":    f"{p['max_alt']}°",
                        "Set":        p["set_time"],
                        "Duration":   p["duration_str"],
                        "Brightness": f"Mag {p['magnitude']}",
                        "Direction":  (f"{p['rise_dir']} → "
                                       f"{p['set_dir']}")
                    })

        if all_visible:
            st.dataframe(
                pd.DataFrame(all_visible),
                hide_index=True, height=300
            )
            st.download_button(
                label="Download visible passes as CSV",
                data=pd.DataFrame(
                    all_visible).to_csv(index=False),
                file_name=(
                    f"satellite_passes_"
                    f"{sat_obs.replace(' ', '_')}_"
                    f"{utcnow().strftime('%Y-%m-%d')}.csv"),
                mime="text/csv"
            )
        else:
            st.info(
                "No visible passes in this window. "
                "Try extending the hours or check "
                "back later — the ISS completes an "
                "orbit every 92 minutes."
            )

        st.markdown("---")
        st.subheader("🎓 About satellite passes")
        st.markdown("""
**Why can I see the ISS?**
The ISS is large — roughly the size of a football
pitch — and covered in solar panels that reflect
sunlight. When it passes overhead during twilight
or night while sunlit, it appears as a fast-moving
bright dot crossing the sky in about 6 minutes.

**When is the best time to look?**
The ISS is only visible when it is in sunlight but
you are in darkness — typically 30 to 90 minutes
after sunset or before sunrise. Passes marked
✅ VISIBLE meet this condition.

**How bright does it get?**
At its brightest the ISS reaches magnitude -5 —
brighter than Venus and visible even in twilight.
Average passes are magnitude -1 to -3.

**How fast does it move?**
The ISS travels at 7.66 km/s — completing one orbit
every 92 minutes. A typical pass lasts 4 to 7 minutes
from horizon to horizon.

**Magnitude scale:**
- Mag -5: Extremely bright — unmissable
- Mag -3: Brighter than Jupiter
- Mag -1: Similar to Sirius (brightest star)
- Mag 0 to 3: Easily visible naked eye
- Mag 4+: Binoculars needed
        """)
        st.caption(
            "Pass predictions use PyEphem with TLE data "
            "from Celestrak. Times are in UTC. "
            "For precise predictions visit "
            "heavens-above.com or n2yo.com"
        )

# ═══════════════════════════════════════════════════════
# TAB 18 — Airmass Calculator
# ═══════════════════════════════════════════════════════
if _vis_sub == "Airmass curve":
    page_header("📐", "Airmass Calculator",
        "Calculate how much atmosphere your telescope "
        "looks through for any target object. "
        "Professional observatories limit observations "
        "to airmass < 2.0. Lower is better.")

    # ── Controls ──────────────────────────────────────────
    am_col1, am_col2 = st.columns([1, 1])

    with am_col1:
        am_obs = st.selectbox(
            "Select observatory",
            df["observatory"].tolist(),
            key="am_obs"
        )
        am_row = df[
            df["observatory"] == am_obs].iloc[0]
        am_lat = float(am_row["latitude"])
        am_lon = float(am_row["longitude"])
        am_alt = float(am_row["altitude_m"] or 0)

    with am_col2:
        am_obj_type = st.selectbox(
            "Object type",
            ["All", "Planets", "Galaxies", "Nebulae",
             "Star Clusters", "Famous Stars",
             "Full Messier Catalogue"],
            key="am_obj_type"
        )

        am_type_map = {
            "All":                    None,
            "Planets":                "planet",
            "Galaxies":               "galaxy",
            "Nebulae":                "nebula",
            "Star Clusters":          "cluster",
            "Famous Stars":           "star",
            "Full Messier Catalogue": "messier",
        }
        am_selected_type = am_type_map[am_obj_type]
        am_filtered = {
            k: v for k, v in OBJECTS.items()
            if am_selected_type is None
            or (am_selected_type == "messier"
                and k.startswith("M") and "—" in k)
            or (am_selected_type is not None
                and am_selected_type != "messier"
                and v["type"] == am_selected_type)
        }

        am_object = st.selectbox(
            "Target object",
            list(am_filtered.keys()),
            key="am_object"
        )

    am_hours = st.slider(
        "Hours to calculate ahead",
        min_value=6, max_value=24,
        value=12, step=2, key="am_hours"
    )

    st.markdown("---")

    # ── Current airmass ───────────────────────────────────
    st.subheader("Current airmass")

    with st.spinner("Calculating airmass..."):
        curve = cached_airmass_curve(am_obs, am_object, am_lat, am_lon, am_alt)

    if not curve:
        st.error(
            "Could not calculate airmass for "
            "this object.")
    else:
        current = curve[0]

        # Current airmass display
        am_val   = current["airmass"]
        am_color = current["color"]
        am_qual  = current["quality"]

        if am_val:
            st.markdown(
                f"<div style='background:{am_color}22;"
                f"border:2px solid {am_color};"
                f"border-radius:8px;padding:16px;"
                f"text-align:center;margin-bottom:16px'>"
                f"<div style='font-size:48px;"
                f"font-weight:bold;color:{am_color}'>"
                f"{am_val}</div>"
                f"<div style='font-size:18px;"
                f"color:{am_color}'>{am_qual}</div>"
                f"<div style='font-size:13px;"
                f"color:#888;margin-top:4px'>"
                f"Airmass for {am_object} "
                f"from {am_obs}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.warning(
                f"{am_object} is currently below "
                f"the horizon at {am_obs}."
            )

        # Metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Airmass",
                  f"{am_val}" if am_val else "—")
        c2.metric("Altitude",
                  f"{current['altitude']}°")
        c3.metric("Azimuth",
                  f"{current['azimuth']}°")
        c4.metric("Extinction",
                  f"{current['extinction']} mag"
                  if current["extinction"] else "—")
        c5.metric("Quality", am_qual)

        st.markdown("---")

        # ── Best window ───────────────────────────────────
        window = get_best_observation_window(curve)
        if window:
            st.subheader("Best observation window tonight")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Best Time",
                      window["best_time"])
            w2.metric("Best Airmass",
                      window["best_airmass"])
            w3.metric("Best Altitude",
                      f"{window['best_alt']}°")
            w4.metric("Good Hours",
                      f"{window['good_hours']}h")

            if window["window_start"]:
                st.info(
                    f"Observable with airmass < 2.0 "
                    f"from **{window['window_start']}** "
                    f"to **{window['window_end']}** UTC "
                    f"({window['good_hours']} hours). "
                    f"Best time: **{window['best_time']}** UTC "
                    f"with airmass "
                    f"**{window['best_airmass']}**."
                )

            st.markdown("---")

        # ── Airmass curve chart ───────────────────────────
        st.subheader(
            f"Airmass curve — next {am_hours} hours")

        # Airmass chart — Plotly
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        times     = [p["time"] for p in curve]
        altitudes = [p["altitude"] for p in curve]
        airmasses = [p["airmass"] if p["airmass"] else None for p in curve]
        is_dark   = [p["is_dark"] for p in curve]
        is_night  = [p["is_night"] for p in curve]
        dot_colors= [p["color"] for p in curve]
        _afig = make_subplots(rows=2, cols=1, row_heights=[0.7,0.3], shared_xaxes=True, vertical_spacing=0.05)
        # Night shading
        for i in range(len(times)-1):
            if is_dark[i]:
                _afig.add_vrect(x0=times[i], x1=times[min(i+1,len(times)-1)], fillcolor="rgba(0,0,51,0.25)", line_width=0, row=1, col=1)
            elif is_night[i]:
                _afig.add_vrect(x0=times[i], x1=times[min(i+1,len(times)-1)], fillcolor="rgba(0,0,80,0.12)", line_width=0, row=1, col=1)
        valid_t  = [times[i] for i,a in enumerate(airmasses) if a]
        valid_am = [a for a in airmasses if a]
        if valid_t:
            _afig.add_trace(go.Scatter(x=valid_t, y=valid_am, mode="lines+markers", line=dict(color="#378ADD", width=2.5), marker=dict(color=dot_colors[:len(valid_t)], size=6), name="Airmass", fill="tonexty", fillcolor="rgba(55,138,221,0.08)"), row=1, col=1)
        _afig.add_hline(y=1.0, line=dict(color="#1D9E75",dash="dash",width=1), annotation_text="Zenith", row=1, col=1)
        _afig.add_hline(y=1.5, line=dict(color="#378ADD",dash="dash",width=1), annotation_text="Good", row=1, col=1)
        _afig.add_hline(y=2.0, line=dict(color="#EF9F27",dash="dash",width=1), annotation_text="Acceptable", row=1, col=1)
        _afig.add_hline(y=3.0, line=dict(color="#E24B4A",dash="dash",width=1), annotation_text="Poor", row=1, col=1)
        _afig.add_trace(go.Scatter(x=times, y=altitudes, mode="lines", line=dict(color="#AFA9EC",width=1.5), name="Altitude (°)"), row=2, col=1)
        _afig.add_hline(y=30, line=dict(color="#378ADD",dash="dash",width=1), row=2, col=1)
        _afig.update_yaxes(title_text="Airmass (lower=better)", autorange="reversed", range=[6.0,0.8], row=1, col=1)
        _afig.update_yaxes(title_text="Altitude (°)", row=2, col=1)
        _afig.update_xaxes(tickangle=45, row=2, col=1)
        _afig.update_layout(
            title=f"Airmass curve — {am_object} from {am_obs}",
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=500, margin=dict(l=50,r=20,t=60,b=60),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(_afig, use_container_width=True)

        st.markdown("---")

        # ── Airmass table ─────────────────────────────────
        st.subheader("Airmass table")
        table_data = []
        for p in curve:
            table_data.append({
                "Time (UTC)":   p["time"],
                "Altitude (°)": p["altitude"],
                "Airmass":      p["airmass"]
                                if p["airmass"] else None,
                "Quality":      p["quality"],
                "Extinction":   p["extinction"]
                                if p["extinction"] else None,
                "Dark Sky":     "🌑" if p["is_dark"]
                                else "🌆" if p["is_night"]
                                else "☀️"
            })
        st.dataframe(
            pd.DataFrame(table_data),
            hide_index=True, height=400
        )

        st.markdown("---")

        # ── Multi-object comparison ───────────────────────
        st.subheader("Compare multiple objects now")
        st.caption(
            "See airmass for all objects of the "
            "selected type from this observatory "
            "right now."
        )

        with st.spinner("Calculating..."):
            comparison = cached_compare_airmass(
                tuple(list(am_filtered.keys())[:30]),
                am_lat, am_lon, am_alt
            )

        visible_objs = [
            o for o in comparison
            if o["visible"]]
        below_horizon = [
            o for o in comparison
            if not o["visible"]]

        st.markdown(
            f"**{len(visible_objs)} objects above "
            f"10° altitude** · "
            f"{len(below_horizon)} below horizon"
        )

        if visible_objs:
            for obj in visible_objs[:15]:
                color = obj["color"]
                am    = (f"{obj['airmass']:.2f}"
                         if obj["airmass"] else "—")
                st.markdown(
                    f"<div style='background:{color}11;"
                    f"border-left:3px solid {color};"
                    f"padding:6px 12px;"
                    f"margin:2px 0;"
                    f"border-radius:4px'>"
                    f"<b>{obj['object']}</b> — "
                    f"Airmass {am} · "
                    f"Alt {obj['altitude']}° · "
                    f"{obj['quality']} · "
                    f"Extinction {obj['extinction']} mag"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info(
                "No objects above 10° altitude "
                "right now from this observatory."
            )

        st.markdown("---")

        # ── Educational section ───────────────────────────
        st.subheader("📖 Understanding airmass")
        st.markdown("""
**What is airmass?**
Airmass (AM) measures how much atmosphere your
telescope looks through compared to looking straight
up. At the zenith (directly overhead) AM = 1.0 —
the minimum possible. Near the horizon AM = 5-10.

**The airmass scale:**
- **AM 1.0** — Zenith. Sharpest possible images.
- **AM 1.5** — 42° altitude. Very good conditions.
- **AM 2.0** — 30° altitude. Acceptable for science.
- **AM 3.0** — 19° altitude. Poor — avoid if possible.
- **AM 5.0+** — Near horizon. Unusable for most work.

**Why does it matter?**
More atmosphere means more turbulence (worse seeing),
more water vapour (worse for infrared), more dust
absorption (dimmer stars), and more atmospheric
dispersion (colour smearing). Professional telescopes
rarely observe above airmass 2.0.

**Atmospheric extinction**
Each airmass unit dims starlight by ~0.18 magnitudes
in visual light. At AM 2.0 your target is 0.36 mag
fainter than at the zenith — significant for photometry.

**The formula**
The simple formula is AM = 1/sin(altitude). The
Pickering (2002) formula used here is more accurate
near the horizon where the simple formula breaks down.
        """)

        st.download_button(
            label="Download airmass table as CSV",
            data=pd.DataFrame(table_data).to_csv(
                index=False),
            file_name=(
                f"airmass_{am_object.replace(' ', '_')}_"
                f"{am_obs.replace(' ', '_')}_"
                f"{utcnow().strftime('%Y-%m-%d')}.csv"),
            mime="text/csv"
        )


# ═══════════════════════════════════════════════════════
# TAB 19 — Meteor Shower Calendar
# ═══════════════════════════════════════════════════════
if _sky_sub == "Meteor Showers":
    page_header("🌠", "Meteor Shower Calendar",
        "Complete calendar of annual meteor showers. "
        "Shows ZHR, moon phase at peak, best viewing "
        "time and observing score for each shower.")

    showers, active, upcoming = cached_showers()
    year     = utcnow().year

    # ── Summary metrics ───────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Showers",    len(showers))
    m2.metric("Active Now",       len(active))
    m3.metric("Next 30 Days",     len(upcoming))
    m4.metric("Best Upcoming",
              upcoming[0]["name"]
              if upcoming else "None")

    st.markdown("---")

    # ── Active showers banner ─────────────────────────────
    if active:
        st.subheader("🔥 Active right now")
        for s in active:
            color = s["status_color"]
            st.markdown(
                f"<div style='background:{color}22;"
                f"border:2px solid {color};"
                f"border-radius:8px;padding:12px;"
                f"margin-bottom:8px'>"
                f"<b style='color:{color};font-size:18px'>"
                f"{s['emoji']} {s['name']}</b> "
                f"<span style='color:{color}'>"
                f"{s['status']}</span><br>"
                f"<span style='color:#ccc'>"
                f"Peak: {s['peak_date']} · "
                f"ZHR: {s['zhr']} · "
                f"Speed: {s['speed_km_s']} km/s · "
                f"Parent: {s['parent']}"
                f"</span></div>",
                unsafe_allow_html=True
            )
        st.markdown("---")

    # ── Year calendar view ────────────────────────────────
    st.subheader(f"📅 {year} Meteor Shower Calendar")

    # Monthly bar chart of ZHR
    month_names = ["Jan", "Feb", "Mar", "Apr", "May",
                   "Jun", "Jul", "Aug", "Sep", "Oct",
                   "Nov", "Dec"]
    monthly_max_zhr = [0] * 12

    for shower in showers:
        m = shower["peak_month"] - 1
        if shower["zhr"] > monthly_max_zhr[m]:
            monthly_max_zhr[m] = shower["zhr"]

    colors_bar = []
    for zhr in monthly_max_zhr:
        if zhr >= 100:  colors_bar.append("#E74C3C")
        elif zhr >= 50: colors_bar.append("#EF9F27")
        elif zhr >= 25: colors_bar.append("#1D9E75")
        elif zhr >= 10: colors_bar.append("#378ADD")
        else:           colors_bar.append("#888888")

    import plotly.graph_objects as go
    _zfig = go.Figure(go.Bar(x=month_names, y=monthly_max_zhr, marker_color=colors_bar, text=monthly_max_zhr, textposition="outside"))
    _zfig.update_layout(
        title=f"Best ZHR by Month — {year}", yaxis_title="Peak ZHR",
        template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
        paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
        height=320, margin=dict(l=40,r=20,t=60,b=40)
    )
    st.plotly_chart(_zfig, use_container_width=True)

    st.markdown("---")

    # ── All showers list ──────────────────────────────────
    st.subheader("All meteor showers — sorted by next peak")

    for s in showers:
        color     = s["status_color"]
        moon      = moon_phase_on_peak(s, year)
        obs_score = observing_score(s, year)
        zhr_q, zhr_c = get_zhr_quality(s["zhr"])

        if obs_score >= 70:   score_color = "#1D9E75"
        elif obs_score >= 50: score_color = "#378ADD"
        elif obs_score >= 30: score_color = "#EF9F27"
        else:                 score_color = "#888888"

        with st.expander(
            f"{s['emoji']} **{s['name']}** — "
            f"Peak: {s['peak_date']} · "
            f"ZHR: {s['zhr']} ({zhr_q}) · "
            f"{s['status']} · "
            f"Score: {obs_score}/100"
        ):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Peak ZHR",    s["zhr"])
            c2.metric("Speed",
                      f"{s['speed_km_s']} km/s")
            c3.metric("Moon at Peak",
                      f"{moon}%" if moon else "N/A")
            c4.metric("Observing Score",
                      f"{obs_score}/100")
            c5.metric("Days Until Peak",
                      s["days_until_peak"])

            d1, d2, d3 = st.columns(3)
            d1.metric("Active",
                      f"{s['active_start']} → "
                      f"{s['active_end']}")
            d2.metric("Best Time",   s["best_time"])
            d3.metric("Hemisphere",  s["hemisphere"])

            st.markdown(
                f"**Parent body:** {s['parent']} · "
                f"**Speed rating:** "
                f"{get_speed_rating(s['speed_km_s'])}"
            )
            st.info(s["description"])

            # Moon phase warning
            if moon and moon > 70:
                st.warning(
                    f"⚠️ Moon is {moon}% illuminated "
                    f"at peak — will wash out faint "
                    f"meteors. Best to observe in "
                    f"early morning before moonrise."
                )
            elif moon and moon < 25:
                st.success(
                    f"✅ Excellent dark sky conditions "
                    f"— moon is only {moon}% illuminated "
                    f"at peak. Perfect for faint meteors."
                )

    st.markdown("---")

    # ── Observing tips ────────────────────────────────────
    st.subheader("🎓 How to observe meteor showers")
    st.markdown("""
**Basic setup:**
- No telescope needed — use your naked eyes
- Let your eyes dark-adapt for 20 minutes
- Lie flat on a reclining chair or sleeping bag
- Look toward the darkest part of the sky
- Face away from the Moon if it is up

**What to look for:**
- Meteors appear as fast streaks of light
- Trace the streak backwards — it points to the radiant
- Fireballs are exceptionally bright meteors (mag < -3)
- Some leave glowing trains lasting several seconds

**Understanding ZHR:**
ZHR (Zenithal Hourly Rate) assumes perfect conditions —
limiting magnitude 6.5, radiant at zenith, no Moon.
Real observed rates are typically 25-50% of ZHR
depending on your sky conditions and location.

**Best conditions:**
- New Moon or Moon below horizon
- Dark sky site away from city lights
- Clear night with low humidity
- Radiant high in the sky (varies by hemisphere)

**Recording observations:**
Count meteors in 15-minute intervals. Note the time,
direction, brightness and colour. Submit to the
International Meteor Organization (imo.net) to
contribute to science.
    """)

    # ── Download calendar ─────────────────────────────────
    st.markdown("---")
    calendar_data = []
    for s in showers:
        moon      = moon_phase_on_peak(s, year)
        obs_score = observing_score(s, year)
        calendar_data.append({
            "Shower":         s["name"],
            "Peak Date":      s["peak_date"],
            "Active Period":  (f"{s['active_start']} — "
                               f"{s['active_end']}"),
            "ZHR":            s["zhr"],
            "Speed (km/s)":   s["speed_km_s"],
            "Parent Body":    s["parent"],
            "Moon at Peak %": moon,
            "Observing Score":obs_score,
            "Best Hemisphere":s["hemisphere"],
            "Best Time":      s["best_time"],
            "Days Until Peak":s["days_until_peak"],
            "Status":         s["status"],
        })

    st.download_button(
        label="Download meteor shower calendar as CSV",
        data=pd.DataFrame(calendar_data).to_csv(
            index=False),
        file_name=(
            f"meteor_showers_{year}.csv"),
        mime="text/csv"
    )


# ═══════════════════════════════════════════════════════
# TAB 20 — Asteroid Tracker
# ═══════════════════════════════════════════════════════
if _sky_sub == "Asteroid Tracker":
    page_header("🪨", "Asteroid Tracker",
        "Real-time near-Earth asteroid data from "
        "NASA's NeoWs API. Shows asteroids passing "
        "Earth with miss distance, size, velocity "
        "and threat assessment.")

    # ── Controls ──────────────────────────────────────────
    days_option = st.select_slider(
        "Time period to look ahead",
        options=[7, 14, 30, 60, 90],
        value=7,
        format_func=lambda x: (
            f"{x} days" if x <= 7
            else f"{x} days "
                 f"({math.ceil(x/7)} API requests)"
        ),
        key="ast_days"
    )

    if days_option > 7:
        st.info(
            f"Fetching {days_option} days requires "
            f"{math.ceil(days_option/7)} API calls. "
            f"Takes 10-30 seconds."
        )

    # ── Fetch button ──────────────────────────────────────
    @st.cache_data(ttl=3600, show_spinner=False)
    def cached_fetch_asteroids(days, cache_key):
        if days <= 7:
            return fetch_asteroids(days_ahead=days)
        else:
            return fetch_asteroids_range(days_ahead=days)

    clicked = st.button(
        "🪨 Fetch Asteroid Data",
        type="primary",
        key="fetch_asteroids_btn"
    )

    if "ast_fetch_count" not in st.session_state:
        st.session_state["ast_fetch_count"] = 0
    if "ast_days_cached" not in st.session_state:
        st.session_state["ast_days_cached"] = 0

    if clicked:
        st.session_state["ast_fetch_count"] += 1
        st.session_state["ast_days_cached"] = days_option

    fetch_count = st.session_state["ast_fetch_count"]
    days_cached = st.session_state["ast_days_cached"]

    if fetch_count == 0:
        asteroids = []
    else:
        with st.spinner("Loading asteroid data..."):
            asteroids = cached_fetch_asteroids(
                days_cached, fetch_count)


    if not asteroids:
        st.info(
            "Click **Fetch Asteroid Data** to load "
            "near-Earth asteroids from NASA's database."
        )
        st.markdown("---")
        st.subheader("🎓 About near-Earth asteroids")
        st.markdown("""
**What is a near-Earth asteroid?**
Near-Earth asteroids (NEAs) are asteroids whose
orbits bring them close to Earth. NASA tracks over
32,000 NEAs and monitors them for potential impact
risk.

**What is a Potentially Hazardous Asteroid (PHA)?**
PHAs are asteroids larger than 140m that come within
0.05 AU (7.5 million km) of Earth's orbit. There are
over 2,300 known PHAs. None are currently on course
to hit Earth in the next 100 years.

**What is a lunar distance (LD)?**
One lunar distance = 384,400 km — the average
distance from Earth to the Moon. Astronomers use
this unit for close asteroid approaches.

**Torino Scale**
The Torino Scale rates asteroid impact risk from
0 (no concern) to 10 (certain collision causing
global catastrophe). All currently known asteroids
are rated 0.
        """)

    else:
        # ALL display code goes here
        stats = get_asteroid_stats(asteroids)

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Total Asteroids",  stats["total"])
        s2.metric("Hazardous (PHAs)", stats["hazardous"])
        s3.metric("Within 1 LD",      stats["within_1ld"])
        s4.metric("Within 5 LD",      stats["within_5ld"])
        s5.metric("Avg Distance",
                  f"{stats['avg_distance_ld']} LD")
        # ... rest of display code

        st.markdown("---")

        # ── Highlight cards ───────────────────────────────
        st.subheader("Key highlights")
        h1, h2, h3 = st.columns(3)

        with h1:
            closest = stats["closest"]
            st.markdown(
                f"<div style='background:#E74C3C22;"
                f"border:1px solid #E74C3C;"
                f"border-radius:8px;padding:12px'>"
                f"<b style='color:#E74C3C'>"
                f"📍 Closest</b><br>"
                f"<b>{closest['name']}</b><br>"
                f"{format_distance(closest['miss_distance_km'])}<br>"
                f"<small>{closest['approach_date']}</small>"
                f"</div>",
                unsafe_allow_html=True
            )

        with h2:
            fastest = stats["fastest"]
            st.markdown(
                f"<div style='background:#EF9F2722;"
                f"border:1px solid #EF9F27;"
                f"border-radius:8px;padding:12px'>"
                f"<b style='color:#EF9F27'>"
                f"⚡ Fastest</b><br>"
                f"<b>{fastest['name']}</b><br>"
                f"{fastest['velocity_km_s']} km/s<br>"
                f"<small>"
                f"{fastest['velocity_km_h']:,.0f} km/h"
                f"</small>"
                f"</div>",
                unsafe_allow_html=True
            )

        with h3:
            largest = stats["largest"]
            st.markdown(
                f"<div style='background:#378ADD22;"
                f"border:1px solid #378ADD;"
                f"border-radius:8px;padding:12px'>"
                f"<b style='color:#378ADD'>"
                f"📏 Largest</b><br>"
                f"<b>{largest['name']}</b><br>"
                f"{largest['diameter_m']}m diameter<br>"
                f"<small>{largest['size_comparison']}</small>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # ── Hazardous alerts ──────────────────────────────
        hazardous_list = [a for a in asteroids
                          if a["hazardous"]]
        if hazardous_list:
            st.subheader(
                f"⚠️ {len(hazardous_list)} Potentially "
                f"Hazardous Asteroids"
            )
            for a in hazardous_list:
                st.warning(
                    f"**{a['name']}** — "
                    f"{format_distance(a['miss_distance_km'])} "
                    f"on {a['approach_date']} · "
                    f"{a['diameter_m']}m "
                    f"({a['size_comparison']}) · "
                    f"{a['velocity_km_s']} km/s · "
                    f"[NASA JPL →]({a['nasa_url']})"
                )
            st.markdown("---")

        # ── Distance bar chart ────────────────────────────
        st.subheader("Miss distances — top 15 closest")
        top15  = asteroids[:15]
        names  = [
            a["name"].replace(
                "(","").replace(")","")[:20]
            for a in top15]
        dists  = [a["miss_distance_lunar"]
                  for a in top15]
        colors = [a["threat_color"] for a in top15]

        import plotly.graph_objects as go
        _abfig = go.Figure(go.Bar(y=names, x=dists, orientation="h", marker_color=colors, text=[f"{d:.1f} LD" for d in dists], textposition="outside"))
        _abfig.add_vline(x=1, line=dict(color="#FFD700", dash="dash", width=1), annotation_text="1 LD (Moon)", annotation_font_color="#FFD700")
        _abfig.add_vline(x=5, line=dict(color="#EF9F27", dash="dash", width=1), annotation_text="5 LD")
        _abfig.update_layout(
            title="Closest Approaching Asteroids", xaxis_title="Miss Distance (Lunar Distances)",
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=420, margin=dict(l=160,r=80,t=60,b=40)
        )
        st.plotly_chart(_abfig, use_container_width=True)

        st.markdown("---")

        # ── Scatter plot ──────────────────────────────────
        st.subheader("Size vs miss distance")
        _asfig = go.Figure()
        for a in asteroids:
            _asfig.add_trace(go.Scatter(
                x=[a["miss_distance_lunar"]], y=[a["diameter_m"]],
                mode="markers",
                marker=dict(color=a["threat_color"], size=10, symbol="diamond" if a["hazardous"] else "circle"),
                name=a["name"], showlegend=False,
                hovertemplate=f"{a['name']}<br>Miss: {a['miss_distance_lunar']:.1f} LD<br>Size: {a['diameter_m']:.0f}m<extra></extra>"
            ))
        _asfig.add_vline(x=1, line=dict(color="#FFD700", dash="dash", width=1), annotation_text="Moon distance")
        _asfig.add_hline(y=140, line=dict(color="#EF9F27", dash="dash", width=1), annotation_text="PHA limit (140m)")
        _asfig.update_layout(
            title="Asteroid Size vs Miss Distance (◆ = Hazardous)",
            xaxis_title="Miss Distance (Lunar Distances)", yaxis_title="Estimated Diameter (m)",
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=420, margin=dict(l=60,r=20,t=60,b=40)
        )
        st.plotly_chart(_asfig, use_container_width=True)

        st.markdown("---")

        # ── Filters ───────────────────────────────────────
        st.subheader(f"All {len(asteroids)} asteroids")

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_haz = st.toggle(
                "Hazardous only",
                value=False, key="filter_haz")
        with fc2:
            filter_size = st.selectbox(
                "Filter by size",
                ["All sizes",
                 "🔴 Large (>1km)",
                 "🟠 Medium (140m-1km)",
                 "🟡 Small (25-140m)",
                 "🟢 Tiny (<25m)"],
                key="filter_size"
            )
        with fc3:
            sort_by = st.selectbox(
                "Sort by",
                ["Date", "Closest first",
                 "Largest first", "Fastest first"],
                key="ast_sort"
            )

        display_list = asteroids.copy()

        if filter_haz:
            display_list = [
                a for a in display_list
                if a["hazardous"]]

        if filter_size != "All sizes":
            display_list = [
                a for a in display_list
                if a["size_class"] == filter_size]

        if sort_by == "Closest first":
            display_list.sort(
                key=lambda x: x["miss_distance_km"])
        elif sort_by == "Largest first":
            display_list.sort(
                key=lambda x: x["diameter_km"],
                reverse=True)
        elif sort_by == "Fastest first":
            display_list.sort(
                key=lambda x: x["velocity_km_s"],
                reverse=True)
        else:
            display_list.sort(
                key=lambda x: x["approach_date"])

        st.caption(
            f"Showing {len(display_list)} of "
            f"{len(asteroids)} asteroids"
        )

        st.markdown("---")

        # ── Timeline by date ──────────────────────────────
        st.subheader("📅 Timeline by approach date")

        from collections import defaultdict
        by_date = defaultdict(list)
        for a in display_list:
            by_date[a["approach_date"]].append(a)

        for date_key in sorted(by_date.keys()):
            day_list  = by_date[date_key]
            haz_count = sum(
                1 for a in day_list if a["hazardous"])
            haz_label = (
                f" — ⚠️ {haz_count} hazardous"
                if haz_count else "")

            st.markdown(
                f"### 📅 {date_key} — "
                f"{len(day_list)} asteroids{haz_label}"
            )

            for a in day_list:
                with st.expander(
                    f"{a['threat_level']} "
                    f"**{a['name']}** — "
                    f"{a['miss_distance_lunar']:.2f} LD "
                    f"({a['miss_distance_km']:,.0f} km)"
                    f" · {a['diameter_m']}m"
                    f" · {a['velocity_km_s']} km/s"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric(
                        "Miss Distance",
                        f"{a['miss_distance_lunar']:.2f} LD")
                    c2.metric(
                        "In km",
                        f"{a['miss_distance_km']:,.0f}")
                    c3.metric(
                        "Diameter",
                        f"{a['diameter_m']}m")
                    c4.metric(
                        "Speed",
                        f"{a['velocity_km_s']} km/s")
                    c5.metric(
                        "Magnitude",
                        f"{a['magnitude']}")

                    st.markdown(
                        f"**Size:** "
                        f"{a['size_comparison']} · "
                        f"**Orbit:** "
                        f"{a['orbit_class']} · "
                        f"**Threat:** "
                        f"{a['threat_desc']}"
                    )

                    if a["impact_energy"]:
                        st.caption(
                            f"⚡ Hypothetical impact: "
                            f"{a['impact_energy']}")

                    if a["hazardous"]:
                        st.warning(
                            f"⚠️ Potentially Hazardous "
                            f"Asteroid — "
                            f"{a['threat_desc']}")

                    st.markdown(
                        f"[🔗 View on NASA JPL →]"
                        f"({a['nasa_url']})")

        st.markdown("---")

        # ── Data table ────────────────────────────────────
        st.subheader("📊 Complete data table")

        table_data = [{
            "Name":           a["name"],
            "Date":           a["approach_date"],
            "Distance (LD)":  a["miss_distance_lunar"],
            "Distance (km)":  a["miss_distance_km"],
            "Diameter (m)":   a["diameter_m"],
            "Speed (km/s)":   a["velocity_km_s"],
            "Hazardous":      a["hazardous"],
            "Threat":         a["threat_level"],
            "Size Class":     a["size_class"],
            "Orbit Class":    a["orbit_class"],
        } for a in display_list]

        st.dataframe(
            pd.DataFrame(table_data),
            hide_index=True,
            height=500
        )

        st.download_button(
            label="Download asteroid data as CSV",
            data=pd.DataFrame(table_data).to_csv(
                index=False),
            file_name=(
                f"asteroids_"
                f"{utcnow().strftime('%Y-%m-%d')}.csv"),
            mime="text/csv"
        )

        st.markdown("---")

        # ── Educational section ───────────────────────────
        st.subheader("🎓 About near-Earth asteroids")
        st.markdown("""
**What is a near-Earth asteroid?**
Near-Earth asteroids (NEAs) are asteroids whose
orbits bring them close to Earth. NASA tracks over
32,000 NEAs and monitors them for potential impact
risk.

**What is a Potentially Hazardous Asteroid (PHA)?**
PHAs are asteroids larger than 140m that come within
0.05 AU (7.5 million km) of Earth's orbit. There are
over 2,300 known PHAs. None are currently on course
to hit Earth in the next 100 years.

**What is a lunar distance (LD)?**
One lunar distance = 384,400 km — the average
distance from Earth to the Moon. Astronomers use
this unit for close asteroid approaches.

**Torino Scale**
The Torino Scale rates asteroid impact risk from
0 (no concern) to 10 (certain collision causing
global catastrophe). All currently known asteroids
are rated 0.

**Size comparison:**
- Chelyabinsk 2013: ~20m — injured 1,500 people
- Tunguska 1908: ~50m — flattened 2,000 km² forest
- Dinosaur extinction: ~10km — global catastrophe
        """)

        st.caption(
            "Data from NASA NeoWs API · "
            "1 LD = 384,400 km · "
            "PHA = Potentially Hazardous Asteroid · "
            "Impact energy is hypothetical only · "
            "No known asteroids are on course "
            "to hit Earth in the foreseeable future"
        )


# ═══════════════════════════════════════════════════════
# TAB 21 — Eclipses & Transits
# ═══════════════════════════════════════════════════════
if _sky_sub == "Eclipses & Transits":
    page_header("🌑", "Eclipses & Transits",
        "Upcoming solar eclipses, lunar eclipses and "
        f"planetary transits. Shows which of your {len(df):,} "
        "observatories have the best view and weather "
        "for each event.")

    events   = cached_eclipse_events()
    upcoming = events[:5]

    # ── Summary metrics ───────────────────────────────────
    solar_count  = sum(1 for e in events
                       if e["category"] == "Solar Eclipse")
    lunar_count  = sum(1 for e in events
                       if e["category"] == "Lunar Eclipse")
    transit_count= sum(1 for e in events
                       if e["category"] == "Transit")
    next_event   = events[0] if events else None

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Solar Eclipses",  solar_count)
    m2.metric("Lunar Eclipses",  lunar_count)
    m3.metric("Transits",        transit_count)
    m4.metric("Next Event",
              f"{next_event['days_until']} days"
              if next_event else "None")

    st.markdown("---")

    # ── Next event banner ─────────────────────────────────
    if next_event:
        color = next_event["color"]
        st.markdown(
            f"<div style='background:{color}22;"
            f"border:2px solid {color};"
            f"border-radius:8px;padding:16px;"
            f"margin-bottom:16px'>"
            f"<h3 style='color:{color};margin:0'>"
            f"{next_event['emoji']} Next: "
            f"{next_event['type']}</h3>"
            f"<p style='color:#ccc;margin:4px 0 0'>"
            f"{next_event['date_display']} · "
            f"In {next_event['days_until']} days · "
            f"{next_event.get('regions', next_event.get('visible_regions', ''))}"
            f"</p></div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Upcoming events list ──────────────────────────────
    st.subheader("All upcoming eclipses and transits")

    # Observatory selector for visibility check
    ecl_obs = st.selectbox(
        "Check visibility from observatory",
        df["observatory"].tolist(),
        key="ecl_obs"
    )
    ecl_row = df[df["observatory"] == ecl_obs].iloc[0]
    ecl_lat = float(ecl_row["latitude"])
    ecl_lon = float(ecl_row["longitude"])
    ecl_alt = float(ecl_row.get("altitude_m", 0) or 0)

    st.markdown("---")

    for event in events:
        color    = event["color"]
        emoji    = event["emoji"]
        days     = event["days_until"]
        category = event["category"]

        # Check visibility from selected observatory
        vis = get_eclipse_visibility(
            event, ecl_lat, ecl_lon, ecl_alt)

        vis_emoji = "✅" if vis["visible"] else "❌"
        in_path   = vis.get("in_totality_path", False)
        if in_path:
            vis_emoji = "🌟"

        with st.expander(
            f"{emoji} **{event['type']}** — "
            f"{event['date_display']} · "
            f"In {days} days · "
            f"{vis_emoji} "
            f"{'IN TOTALITY PATH!' if in_path else 'Visible' if vis['visible'] else 'Not visible'} "
            f"from {ecl_obs.replace(' Observatory', '')[:20]}"
        ):
            # Key metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date",     event["date_display"])
            c2.metric("Days Away",days)
            c3.metric("Category", category)
            c4.metric("Type",     event["type"])

            # Eclipse-specific metrics
            if category == "Solar Eclipse":
                s1, s2, s3 = st.columns(3)
                s1.metric("Magnitude",
                          event.get("magnitude", "N/A"))
                s2.metric("Max Duration",
                          f"{event.get('duration_mins', 0)} min"
                          if event.get("duration_mins")
                          else "N/A")
                s3.metric("Regions",
                          event.get("regions", "N/A"))

            elif category == "Lunar Eclipse":
                l1, l2, l3, l4 = st.columns(4)
                l1.metric("Magnitude",
                          event.get("magnitude", "N/A"))
                l2.metric("Totality",
                          f"{event.get('duration_totality', 0)} min"
                          if event.get("duration_totality")
                          else "Partial")
                l3.metric("Max Eclipse",
                          event.get("max_eclipse", "N/A"))
                l4.metric("Visible From",
                          event.get("visible_regions", "N/A"))

                if event.get("totality_start"):
                    t1, t2, t3 = st.columns(3)
                    t1.metric("Partial Starts",
                              event.get("partial_start", "N/A"))
                    t2.metric("Totality Starts",
                              event.get("totality_start", "N/A"))
                    t3.metric("Totality Ends",
                              event.get("totality_end", "N/A"))

            elif category == "Transit":
                tr1, tr2, tr3 = st.columns(3)
                tr1.metric("Start",    event.get("start", "N/A"))
                tr2.metric("Mid",      event.get("mid", "N/A"))
                tr3.metric("End",      event.get("end", "N/A"))
                st.info(f"**Rarity:** {event.get('rarity', 'N/A')}")

            # Description
            st.info(event["description"])

            # Visibility from selected observatory
            st.markdown(
                f"**Visibility from {ecl_obs}:**"
            )
            if in_path:
                st.success(
                    f"🌟 **This observatory is inside "
                    f"the path of totality!** "
                    f"{vis['reason']}"
                )
            elif vis["visible"]:
                st.success(
                    f"✅ Visible from this observatory. "
                    f"{vis['reason']}"
                )
            else:
                st.warning(
                    f"❌ Not visible from this location. "
                    f"{vis['reason']}"
                )

            # Rarity
            st.caption(eclipse_rarity(event))

            st.markdown("---")

            # Best observatories for this eclipse
            st.markdown(
                f"**Best observatories for "
                f"this {event['type'].lower()}:**"
            )

            with st.spinner("Finding best observatories..."):
                best_obs = cached_best_obs_for_eclipse(
                    event.get("name",""), event.get("date",""))

            if best_obs:
                for obs in best_obs[:5]:
                    path_badge = (
                        " 🌟 IN TOTALITY PATH"
                        if obs["in_totality"] else "")
                    st.markdown(
                        f"**{obs['observatory']}** "
                        f"({obs['country']}) · "
                        f"Weather: {obs['weather_score']}/100"
                        f"{path_badge}"
                    )
            else:
                st.info(
                    "Visibility calculations running..."
                )

    st.markdown("---")

    # ── Solar eclipse timeline chart ──────────────────────
    st.subheader("📅 Eclipse timeline")

    solar_events  = [e for e in events
                     if e["category"] == "Solar Eclipse"]
    lunar_events  = [e for e in events
                     if e["category"] == "Lunar Eclipse"]

    if solar_events or lunar_events:
        import plotly.graph_objects as go
        colors_map = {"total":"#E74C3C","annular":"#F39C12","partial":"#EF9F27"}
        _efig = go.Figure()
        for e in solar_events[:8]:
            color = colors_map.get(e.get("subtype","partial"),"#EF9F27")
            days  = e["days_until"]
            _efig.add_trace(go.Bar(x=[30], y=["Solar"], base=[days], orientation="h", marker_color=color, showlegend=False, hovertemplate=f"{e['type']}<br>{e['date']}<extra></extra>", text=e["type"].replace(" Solar",""), textposition="inside"))
        for e in lunar_events[:8]:
            color = "#E74C3C" if e.get("subtype")=="total" else "#EF9F27"
            days  = e["days_until"]
            _efig.add_trace(go.Bar(x=[20], y=["Lunar"], base=[days], orientation="h", marker_color=color, showlegend=False, hovertemplate=f"{e['type']}<br>{e['date']}<extra></extra>", text="Total" if e.get("subtype")=="total" else "Partial", textposition="inside"))
        _efig.update_layout(
            title="Upcoming Eclipse Timeline", xaxis_title="Days from today",
            barmode="overlay",
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=280, margin=dict(l=80,r=20,t=60,b=40)
        )
        st.plotly_chart(_efig, use_container_width=True)

    st.markdown("---")

    # ── Educational section ───────────────────────────────
    st.subheader("🎓 Understanding eclipses")
    st.markdown("""
**Solar eclipses** occur when the Moon passes between
Earth and the Sun. The Moon's shadow falls on Earth.

**Types of solar eclipse:**
- **Total** — Moon completely covers the Sun. The corona
  becomes visible. Day turns to night. Lasts up to 7.5 min.
- **Annular** — Moon is too far away to fully cover the Sun.
  A ring of fire remains visible around the Moon.
- **Partial** — Only part of the Sun is covered. Requires
  solar filters to observe safely at all times.
- **Hybrid** — Starts annular, becomes total, then annular.
  Very rare.

**Lunar eclipses** occur when Earth passes between the
Sun and Moon. Earth's shadow falls on the Moon.

**Types of lunar eclipse:**
- **Total** — Moon enters Earth's umbra completely.
  Turns red/orange due to sunlight refracted by Earth's
  atmosphere. Safe to observe with naked eye.
- **Partial** — Only part of the Moon enters the umbra.
- **Penumbral** — Moon passes through Earth's outer shadow.
  Very subtle darkening — hard to notice.

**Transits** occur when Mercury or Venus crosses the
Sun's disc as seen from Earth. Appears as a tiny black
dot moving slowly across the Sun. Requires solar filter.

**Safety:**
Never look at a solar eclipse without certified solar
filters (ISO 12312-2). Regular sunglasses are NOT safe.
Lunar eclipses are completely safe to observe.
    """)

# ═══════════════════════════════════════════════════════
# TAB 22 — Meteor Showers   
# ═══════════════════════════════════════════════════════
if _detail_sub == "Live detail":
    st.caption(
        "Complete live analysis calculated in real time. Weather data "
        "is updated hourly; astronomical calculations are computed "
        "fresh when you select a site.")

    selected = st.selectbox(
        "Select an observatory",
        df["observatory"].tolist(),
        key="detail_obs"
    )

    row = df[df["observatory"] == selected].iloc[0]

    with st.spinner(
        f"Calculating live conditions for {selected}..."
    ):
        from live_calculator import calculate_live_conditions
        live = calculate_live_conditions(row)

    # ── Google Maps / Earth links ──────────────────────────
    gmap_url   = (
        f"https://www.google.com/maps/search/?api=1"
        f"&query={live['latitude']},{live['longitude']}"
    )
    gearth_url = (
        f"https://earth.google.com/web/@"
        f"{live['latitude']},{live['longitude']},"
        f"{live['altitude_m']}a,5000d,35y,0h,0t,0r"
    )
    street_url = (
        f"https://www.google.com/maps/@"
        f"{live['latitude']},{live['longitude']},14z"
    )

    link1, link2, link3 = st.columns(3)
    with link1:
        st.markdown(f"[🌍 Open in Google Earth]({gearth_url})")
    with link2:
        st.markdown(f"[🗺️ Open in Google Maps]({gmap_url})")
    with link3:
        st.markdown(f"[📍 Street View]({street_url})")

    # ── Header ────────────────────────────────────────────
    score = live["observation_score"]
    if score >= 80:   banner_color = "#1D9E75"
    elif score >= 60: banner_color = "#378ADD"
    elif score >= 40: banner_color = "#EF9F27"
    else:             banner_color = "#E24B4A"

    st.markdown(
        f"<div style='background:{banner_color}22;"
        f"border:2px solid {banner_color};"
        f"border-radius:8px;padding:16px;"
        f"margin-bottom:16px'>"
        f"<h3 style='color:{banner_color};margin:0'>"
        f"{selected}</h3>"
        f"<p style='color:#ccc;margin:4px 0 0'>"
        f"{live['country']} · "
        f"{live['altitude_m']}m altitude · "
        f"Score: {score}/100 · "
        f"Sky: {live['sky_state']}</p>"
        f"<p style='color:#888;font-size:12px;"
        f"margin:4px 0 0'>"
        f"Weather fetched: {live['fetch_datetime']} · "
        f"Calculated: {live['calculated_at']}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Weather metrics ───────────────────────────────────
    st.subheader("Current weather")
    w1, w2, w3, w4, w5 = st.columns(5)
    w1.metric("Score",       f"{live['observation_score']}/100")
    w2.metric("Cloud Cover", f"{live['cloud_cover_pct']}%")
    w3.metric("Humidity",    f"{live['humidity_pct']}%")
    w4.metric("Wind Speed",  f"{live['wind_speed_ms']} m/s")
    w5.metric("Temperature", f"{live['temperature_c']}°C")

    st.markdown("---")

    # ── Sky state ─────────────────────────────────────────
    st.subheader("Current sky state")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Sky State",    live["sky_state"])
    s2.metric("Sun Altitude", f"{live['sun_altitude']}°")
    s3.metric("Moon Altitude",f"{live['moon_altitude']}°")
    s4.metric("Moon Phase",   f"{live['moon_phase_pct']}%")
    s5.metric("Is Dark Now",
              "Yes 🌑" if live["is_dark"] else "No ☀️")

    st.markdown("---")

    # ── Atmospheric analysis ──────────────────────────────
    st.subheader("Atmospheric conditions")
    a1, a2, a3 = st.columns(3)
    a1.metric("Seeing",
              f"{live['seeing_arcsec']}\"",
              live["seeing_quality"])
    a2.metric("PWV",
              f"{live['pwv_mm']} mm",
              live["pwv_quality"])
    a3.metric("Jet Stream",
              f"{live['jet_stream_ms']} m/s",
              live["jet_impact"])

    st.markdown("---")

    # ── Tonight's window ──────────────────────────────────
    st.subheader("Tonight's observing window")
    tw1, tw2, tw3, tw4, tw5 = st.columns(5)
    tw1.metric("Dark Start",  live["dark_start"])
    tw2.metric("Dark End",    live["dark_end"])
    tw3.metric("Dark Hours",  f"{live['dark_hours']}h")
    tw4.metric("Moon Rise",   live["moon_rise"])
    tw5.metric("Final Score", f"{live['final_score']}/100")

    st.markdown("---")

    # ── Peak observing time ───────────────────────────────
    st.subheader("Peak observing time tonight")
    p1, p2, p3 = st.columns(3)
    p1.metric("Peak Hour",   live["peak_hour"])
    p2.metric("Peak Score",  f"{live['peak_score']}/100")
    p3.metric("Good Hours",  f"{live['total_good_hours']}h")

    if live["hourly_data"]:
        hours  = [h["hour"] for h in live["hourly_data"]]
        scores = [h["combined_score"] for h in live["hourly_data"]]
        colors = []
        for s in scores:
            if s >= 80:   colors.append("#1D9E75")
            elif s >= 60: colors.append("#378ADD")
            elif s >= 40: colors.append("#EF9F27")
            elif s > 0:   colors.append("#E24B4A")
            else:         colors.append("#444441")

        import plotly.graph_objects as go
        _dlabels = [f"{h:02d}:00" for h in range(24)]
        _dpeak   = scores.index(max(scores)) if scores else 0
        _dfig = go.Figure(go.Bar(x=_dlabels, y=scores, marker_color=colors, hovertemplate="%{x}<br>Score: %{y:.0f}/100<extra></extra>"))
        _dfig.add_annotation(x=_dlabels[_dpeak], y=scores[_dpeak]+8, text=f"Peak<br>{scores[_dpeak]:.0f}/100", showarrow=False, font=dict(color="white",size=10), bgcolor="rgba(29,158,117,0.3)", bordercolor="#1D9E75", borderwidth=1)
        _dfig.update_layout(
            title=f"Hourly observing score — {selected}",
            yaxis=dict(range=[0,110], title="Score"), xaxis_title="Hour (UTC)",
            template="plotly_dark" if st.session_state.theme=="dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=320, margin=dict(l=40,r=20,t=60,b=60)
        )
        st.plotly_chart(_dfig, use_container_width=True)

    st.markdown("---")

    # ── Website and live camera ───────────────────────────
    from sky_chart import get_observatory_url, get_live_camera

    obs_url = get_observatory_url(selected)
    st.markdown(
        f"🌐 **[Visit observatory website or search →]({obs_url})**"
    )

    cam = get_live_camera(selected)
    if cam:
        st.subheader("📷 Live Camera Feed")
        st.success(
            f"**{cam['name']}** — {cam['description']} · "
            f"Credit: {cam['credit']}"
        )
        st.markdown(f"[🔴 Open full live feed →]({cam['page_url']})")
        try:
            st.image(
                cam["image_url"],
                caption=f"Live feed — {cam['name']} — {cam['description']}",
                width='stretch'
            )
        except Exception:
            st.info(
                "Camera image unavailable right now. "
                f"[View directly →]({cam['page_url']})"
            )
    else:
        st.subheader("📷 Live Camera Feed")
        st.info(
            "No public live camera feed available "
            "for this observatory. Most smaller "
            "observatories do not publish live feeds."
        )

    st.markdown("---")

    # ── Mini location map ─────────────────────────────────
    st.subheader("Location")
    import plotly.graph_objects as go
    _nearby = df[
        (abs(df["latitude"]  - live["latitude"])  < 15) &
        (abs(df["longitude"] - live["longitude"]) < 15) &
        (df["observatory"] != selected)
    ].nlargest(8, "observation_score")

    _det_fig = go.Figure()
    # nearby sites (grey)
    if not _nearby.empty:
        _det_fig.add_trace(go.Scattermapbox(
            lat=_nearby["latitude"], lon=_nearby["longitude"],
            mode="markers",
            marker=dict(size=7, color="#5c7a96", opacity=0.7),
            text=_nearby["observatory"],
            hovertemplate="<b>%{text}</b><extra></extra>",
            name="Nearby",
        ))
    # selected site (gold star)
    _det_fig.add_trace(go.Scattermapbox(
        lat=[live["latitude"]], lon=[live["longitude"]],
        mode="markers+text",
        marker=dict(size=16, color="#f4a261"),
        text=[selected.split(" Observatory")[0].split(" Telescope")[0]],
        textposition="top right",
        textfont=dict(color="#f4a261", size=12),
        hovertemplate=f"<b>{selected}</b><br>{live['latitude']}°, {live['longitude']}°<extra></extra>",
        name=selected,
    ))
    _det_fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=live["latitude"], lon=live["longitude"]), zoom=5),
        margin=dict(l=0, r=0, t=0, b=0), height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(bgcolor="rgba(10,10,20,0.7)", bordercolor="#1e2d40", borderwidth=1, font=dict(color="#cdd9e5", size=11)),
        showlegend=True,
    )
    st.plotly_chart(_det_fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": False})

    # ── Nearby observatories ──────────────────────────────
    if not _nearby.empty:
        st.subheader("Nearby observatories")
        _nb_cols = st.columns(min(4, len(_nearby)))
        for _ni, (_, _nr) in enumerate(_nearby.iterrows()):
            with _nb_cols[_ni % 4]:
                _nb_color = {"Excellent": "#1D9E75", "Good": "#00b4d8", "Marginal": "#EF9F27", "Poor": "#E24B4A"}.get(_nr["condition"], "#888")
                st.markdown(
                    f"<div style='background:#0e1117;border:1px solid #1e2d40;border-left:3px solid {_nb_color};"
                    f"border-radius:6px;padding:10px;font-size:12px'>"
                    f"<div style='color:#cdd9e5;font-weight:600'>{_nr['observatory']}</div>"
                    f"<div style='color:{_nb_color};font-weight:700'>{int(_nr['observation_score'])}/100 · {_nr['condition']}</div>"
                    f"<div style='color:#5c7a96'>Cloud {_nr['cloud_cover_pct']}% · Wind {_nr['wind_speed_ms']} m/s</div>"
                    f"</div>", unsafe_allow_html=True
                )

    st.markdown("---")

    # ── Historical reliability summary ────────────────────
    st.subheader("Historical reliability (last 30 days)")
    _rel_df = cached_reliability_scores(30)
    if not _rel_df.empty and selected in _rel_df["observatory"].values:
        _rel_row = _rel_df[_rel_df["observatory"] == selected].iloc[0]
        _rh1, _rh2, _rh3, _rh4 = st.columns(4)
        _rh1.metric("Reliability Grade", _rel_row.get("grade", "N/A"))
        _rh2.metric("Avg Score", f"{round(_rel_row.get('avg_score', 0), 1)}/100")
        _rh3.metric("Excellent Nights", f"{_rel_row.get('pct_excellent', 0)}%")
        _rh4.metric("Poor Nights", f"{_rel_row.get('pct_poor', 0)}%")
        # Sparkline using pct breakdown
        _spark_labels = ["Excellent", "Good", "Marginal", "Poor"]
        _spark_values = [
            _rel_row.get("pct_excellent", 0),
            max(0, _rel_row.get("pct_good", 0) - _rel_row.get("pct_excellent", 0)),
            max(0, 100 - _rel_row.get("pct_good", 0) - _rel_row.get("pct_poor", 0)),
            _rel_row.get("pct_poor", 0),
        ]
        _spark_colors = ["#1D9E75", "#00b4d8", "#EF9F27", "#E24B4A"]
        _sfig = go.Figure(go.Bar(
            x=_spark_labels, y=_spark_values,
            marker_color=_spark_colors,
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))
        _sfig.update_layout(
            yaxis=dict(range=[0, 105], title="% of nights"),
            template="plotly_dark" if st.session_state.theme == "dark" else "plotly_white",
            paper_bgcolor=BG2, plot_bgcolor=BG2, font=dict(color=TEXT),
            height=220, margin=dict(l=40, r=20, t=10, b=40),
        )
        st.plotly_chart(_sfig, use_container_width=True)
    else:
        st.info("No historical data available for this observatory yet.")

    st.markdown("---")
    st.info(
        f"**{selected}** is located at "
        f"{live['latitude']}°, {live['longitude']}° "
        f"in {live['country']} at {live['altitude_m']}m altitude. "
        f"All astronomical calculations are performed "
        f"live when you select this observatory."
    )


# ═══════════════════════════════════════════════════════
# GLOBAL FOOTER — rendered on every page
# ═══════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:48px;padding:18px 0 8px;border-top:1px solid {BORDER};
            display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;
            justify-content:center;font-size:0.74rem;color:{TEXT2};">
  <span style="font-weight:700;color:{TEXT};letter-spacing:0.04em;">GOWC</span>
  <span>·</span>
  <span>Global Observatory Weather Tracker</span>
  <span>·</span>
  <span>Weather data: <a href="https://open-meteo.com" target="_blank"
        style="color:{ACCENT};text-decoration:none;">Open-Meteo</a></span>
  <span>·</span>
  <span>Built by Ahzam Ahmed</span>
  <span>·</span>
  <span>Forecasts are estimates for planning, not official observatory conditions.</span>
</div>
""", unsafe_allow_html=True)