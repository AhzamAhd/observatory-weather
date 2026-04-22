import ephem
import math
from datetime import datetime
import pandas as pd

OBJECTS = {
    # ── Planets ──────────────────────────────────────────────────
    "Mercury":          {"type": "planet", "obj": ephem.Mercury},
    "Venus":            {"type": "planet", "obj": ephem.Venus},
    "Mars":             {"type": "planet", "obj": ephem.Mars},
    "Jupiter":          {"type": "planet", "obj": ephem.Jupiter},
    "Saturn":           {"type": "planet", "obj": ephem.Saturn},
    "Uranus":           {"type": "planet", "obj": ephem.Uranus},
    "Neptune":          {"type": "planet", "obj": ephem.Neptune},

    # ── Dwarf planets & asteroids ─────────────────────────────────
    "Pluto":            {"type": "dwarf_planet", "obj": ephem.Pluto},
    "Ceres":            {"type": "asteroid", "ra": "3:36:00",  "dec": "22:48:00"},
    "Vesta":            {"type": "asteroid", "ra": "8:12:00",  "dec": "20:12:00"},
    "Pallas":           {"type": "asteroid", "ra": "3:00:00",  "dec": "18:00:00"},
    "Eris":             {"type": "dwarf_planet", "ra": "1:46:00", "dec": "-1:42:00"},
    "Makemake":         {"type": "dwarf_planet", "ra": "12:45:00", "dec": "29:00:00"},
    "Haumea":           {"type": "dwarf_planet", "ra": "14:00:00", "dec": "18:00:00"},

    # ── Full Messier Catalogue ────────────────────────────────────
    "M1 — Crab Nebula":             {"type": "nebula",  "ra": "5:34:32",  "dec": "22:00:52"},
    "M2 — Globular Cluster":        {"type": "cluster", "ra": "21:33:27", "dec": "-0:49:24"},
    "M3 — Globular Cluster":        {"type": "cluster", "ra": "13:42:11", "dec": "28:22:38"},
    "M4 — Globular Cluster":        {"type": "cluster", "ra": "16:23:35", "dec": "-26:31:33"},
    "M5 — Globular Cluster":        {"type": "cluster", "ra": "15:18:34", "dec": "2:04:58"},
    "M6 — Butterfly Cluster":       {"type": "cluster", "ra": "17:40:21", "dec": "-32:15:12"},
    "M7 — Ptolemy Cluster":         {"type": "cluster", "ra": "17:53:51", "dec": "-34:47:34"},
    "M8 — Lagoon Nebula":           {"type": "nebula",  "ra": "18:03:37", "dec": "-24:23:12"},
    "M9 — Globular Cluster":        {"type": "cluster", "ra": "17:19:12", "dec": "-18:30:58"},
    "M10 — Globular Cluster":       {"type": "cluster", "ra": "16:57:09", "dec": "-4:05:58"},
    "M11 — Wild Duck Cluster":      {"type": "cluster", "ra": "18:51:05", "dec": "-6:16:12"},
    "M12 — Globular Cluster":       {"type": "cluster", "ra": "16:47:14", "dec": "-1:56:52"},
    "M13 — Hercules Cluster":       {"type": "cluster", "ra": "16:41:41", "dec": "36:27:37"},
    "M14 — Globular Cluster":       {"type": "cluster", "ra": "17:37:36", "dec": "-3:14:45"},
    "M15 — Globular Cluster":       {"type": "cluster", "ra": "21:29:58", "dec": "12:10:01"},
    "M16 — Eagle Nebula":           {"type": "nebula",  "ra": "18:18:48", "dec": "-13:47:00"},
    "M17 — Omega Nebula":           {"type": "nebula",  "ra": "18:20:26", "dec": "-16:10:36"},
    "M18 — Open Cluster":           {"type": "cluster", "ra": "18:19:58", "dec": "-17:06:06"},
    "M19 — Globular Cluster":       {"type": "cluster", "ra": "17:02:38", "dec": "-26:16:05"},
    "M20 — Trifid Nebula":          {"type": "nebula",  "ra": "18:02:23", "dec": "-23:01:48"},
    "M21 — Open Cluster":           {"type": "cluster", "ra": "18:04:13", "dec": "-22:29:24"},
    "M22 — Globular Cluster":       {"type": "cluster", "ra": "18:36:24", "dec": "-23:54:12"},
    "M23 — Open Cluster":           {"type": "cluster", "ra": "17:56:54", "dec": "-19:01:00"},
    "M24 — Sagittarius Star Cloud": {"type": "cluster", "ra": "18:16:56", "dec": "-18:33:00"},
    "M25 — Open Cluster":           {"type": "cluster", "ra": "18:31:47", "dec": "-19:07:00"},
    "M26 — Open Cluster":           {"type": "cluster", "ra": "18:45:18", "dec": "-9:23:00"},
    "M27 — Dumbbell Nebula":        {"type": "nebula",  "ra": "19:59:36", "dec": "22:43:16"},
    "M28 — Globular Cluster":       {"type": "cluster", "ra": "18:24:33", "dec": "-24:52:12"},
    "M29 — Open Cluster":           {"type": "cluster", "ra": "20:23:56", "dec": "38:30:28"},
    "M30 — Globular Cluster":       {"type": "cluster", "ra": "21:40:22", "dec": "-23:10:45"},
    "M31 — Andromeda Galaxy":       {"type": "galaxy",  "ra": "0:42:44",  "dec": "41:16:09"},
    "M32 — Dwarf Elliptical":       {"type": "galaxy",  "ra": "0:42:42",  "dec": "40:51:55"},
    "M33 — Triangulum Galaxy":      {"type": "galaxy",  "ra": "1:33:51",  "dec": "30:39:37"},
    "M34 — Open Cluster":           {"type": "cluster", "ra": "2:42:05",  "dec": "42:47:00"},
    "M35 — Open Cluster":           {"type": "cluster", "ra": "6:08:54",  "dec": "24:20:00"},
    "M36 — Open Cluster":           {"type": "cluster", "ra": "5:36:18",  "dec": "34:08:27"},
    "M37 — Open Cluster":           {"type": "cluster", "ra": "5:52:18",  "dec": "32:33:11"},
    "M38 — Open Cluster":           {"type": "cluster", "ra": "5:28:43",  "dec": "35:51:18"},
    "M39 — Open Cluster":           {"type": "cluster", "ra": "21:31:48", "dec": "48:26:00"},
    "M40 — Double Star":            {"type": "star",    "ra": "12:22:12", "dec": "58:04:48"},
    "M41 — Open Cluster":           {"type": "cluster", "ra": "6:46:01",  "dec": "-20:45:24"},
    "M42 — Orion Nebula":           {"type": "nebula",  "ra": "5:35:17",  "dec": "-5:23:28"},
    "M43 — De Mairan Nebula":       {"type": "nebula",  "ra": "5:35:31",  "dec": "-5:16:12"},
    "M44 — Beehive Cluster":        {"type": "cluster", "ra": "8:40:24",  "dec": "19:40:00"},
    "M45 — Pleiades":               {"type": "cluster", "ra": "3:47:24",  "dec": "24:07:00"},
    "M46 — Open Cluster":           {"type": "cluster", "ra": "7:41:46",  "dec": "-14:48:36"},
    "M47 — Open Cluster":           {"type": "cluster", "ra": "7:36:35",  "dec": "-14:28:57"},
    "M48 — Open Cluster":           {"type": "cluster", "ra": "8:13:43",  "dec": "-5:45:00"},
    "M49 — Elliptical Galaxy":      {"type": "galaxy",  "ra": "12:29:47", "dec": "8:00:02"},
    "M50 — Open Cluster":           {"type": "cluster", "ra": "7:02:42",  "dec": "-8:23:00"},
    "M51 — Whirlpool Galaxy":       {"type": "galaxy",  "ra": "13:29:53", "dec": "47:11:43"},
    "M52 — Open Cluster":           {"type": "cluster", "ra": "23:24:48", "dec": "61:35:36"},
    "M53 — Globular Cluster":       {"type": "cluster", "ra": "13:12:55", "dec": "18:10:09"},
    "M54 — Globular Cluster":       {"type": "cluster", "ra": "18:55:04", "dec": "-30:28:47"},
    "M55 — Globular Cluster":       {"type": "cluster", "ra": "19:39:59", "dec": "-30:57:44"},
    "M56 — Globular Cluster":       {"type": "cluster", "ra": "19:16:35", "dec": "30:11:05"},
    "M57 — Ring Nebula":            {"type": "nebula",  "ra": "18:53:35", "dec": "33:01:45"},
    "M58 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:37:44", "dec": "11:49:05"},
    "M59 — Elliptical Galaxy":      {"type": "galaxy",  "ra": "12:42:02", "dec": "11:38:49"},
    "M60 — Elliptical Galaxy":      {"type": "galaxy",  "ra": "12:43:40", "dec": "11:33:09"},
    "M61 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:21:55", "dec": "4:28:25"},
    "M62 — Globular Cluster":       {"type": "cluster", "ra": "17:01:13", "dec": "-30:06:45"},
    "M63 — Sunflower Galaxy":       {"type": "galaxy",  "ra": "13:15:49", "dec": "42:01:45"},
    "M64 — Black Eye Galaxy":       {"type": "galaxy",  "ra": "12:56:44", "dec": "21:40:58"},
    "M65 — Spiral Galaxy":          {"type": "galaxy",  "ra": "11:18:56", "dec": "13:05:32"},
    "M66 — Spiral Galaxy":          {"type": "galaxy",  "ra": "11:20:15", "dec": "12:59:30"},
    "M67 — Open Cluster":           {"type": "cluster", "ra": "8:51:18",  "dec": "11:48:00"},
    "M68 — Globular Cluster":       {"type": "cluster", "ra": "12:39:28", "dec": "-26:44:34"},
    "M69 — Globular Cluster":       {"type": "cluster", "ra": "18:31:23", "dec": "-32:20:53"},
    "M70 — Globular Cluster":       {"type": "cluster", "ra": "18:43:12", "dec": "-32:17:31"},
    "M71 — Globular Cluster":       {"type": "cluster", "ra": "19:53:46", "dec": "18:46:42"},
    "M72 — Globular Cluster":       {"type": "cluster", "ra": "20:53:28", "dec": "-12:32:14"},
    "M73 — Asterism":               {"type": "cluster", "ra": "20:58:56", "dec": "-12:38:08"},
    "M74 — Phantom Galaxy":         {"type": "galaxy",  "ra": "1:36:42",  "dec": "15:47:01"},
    "M75 — Globular Cluster":       {"type": "cluster", "ra": "20:06:05", "dec": "-21:55:17"},
    "M76 — Little Dumbbell":        {"type": "nebula",  "ra": "1:42:20",  "dec": "51:34:31"},
    "M77 — Seyfert Galaxy":         {"type": "galaxy",  "ra": "2:42:41",  "dec": "-0:00:48"},
    "M78 — Reflection Nebula":      {"type": "nebula",  "ra": "5:46:46",  "dec": "0:04:45"},
    "M79 — Globular Cluster":       {"type": "cluster", "ra": "5:24:11",  "dec": "-24:31:27"},
    "M80 — Globular Cluster":       {"type": "cluster", "ra": "16:17:02", "dec": "-22:58:34"},
    "M81 — Bode's Galaxy":          {"type": "galaxy",  "ra": "9:55:33",  "dec": "69:03:55"},
    "M82 — Cigar Galaxy":           {"type": "galaxy",  "ra": "9:55:52",  "dec": "69:40:47"},
    "M83 — Southern Pinwheel":      {"type": "galaxy",  "ra": "13:37:01", "dec": "-29:51:57"},
    "M84 — Lenticular Galaxy":      {"type": "galaxy",  "ra": "12:25:04", "dec": "12:53:13"},
    "M85 — Lenticular Galaxy":      {"type": "galaxy",  "ra": "12:25:24", "dec": "18:11:28"},
    "M86 — Lenticular Galaxy":      {"type": "galaxy",  "ra": "12:26:12", "dec": "12:56:45"},
    "M87 — Virgo A Galaxy":         {"type": "galaxy",  "ra": "12:30:49", "dec": "12:23:28"},
    "M88 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:31:59", "dec": "14:25:14"},
    "M89 — Elliptical Galaxy":      {"type": "galaxy",  "ra": "12:35:40", "dec": "12:33:23"},
    "M90 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:36:50", "dec": "13:09:46"},
    "M91 — Barred Spiral":          {"type": "galaxy",  "ra": "12:35:26", "dec": "14:29:47"},
    "M92 — Globular Cluster":       {"type": "cluster", "ra": "17:17:07", "dec": "43:08:11"},
    "M93 — Open Cluster":           {"type": "cluster", "ra": "7:44:30",  "dec": "-23:51:11"},
    "M94 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:50:53", "dec": "41:07:14"},
    "M95 — Barred Spiral":          {"type": "galaxy",  "ra": "10:43:58", "dec": "11:42:14"},
    "M96 — Spiral Galaxy":          {"type": "galaxy",  "ra": "10:46:46", "dec": "11:49:12"},
    "M97 — Owl Nebula":             {"type": "nebula",  "ra": "11:14:48", "dec": "55:01:09"},
    "M98 — Spiral Galaxy":          {"type": "galaxy",  "ra": "12:13:48", "dec": "14:54:01"},
    "M99 — Coma Pinwheel":          {"type": "galaxy",  "ra": "12:18:50", "dec": "14:24:59"},
    "M100 — Grand Design Spiral":   {"type": "galaxy",  "ra": "12:22:55", "dec": "15:49:21"},
    "M101 — Pinwheel Galaxy":       {"type": "galaxy",  "ra": "14:03:13", "dec": "54:20:56"},
    "M102 — Spindle Galaxy":        {"type": "galaxy",  "ra": "15:06:29", "dec": "55:45:48"},
    "M103 — Open Cluster":          {"type": "cluster", "ra": "1:33:23",  "dec": "60:39:00"},
    "M104 — Sombrero Galaxy":       {"type": "galaxy",  "ra": "12:39:59", "dec": "-11:37:23"},
    "M105 — Elliptical Galaxy":     {"type": "galaxy",  "ra": "10:47:49", "dec": "12:34:54"},
    "M106 — Spiral Galaxy":         {"type": "galaxy",  "ra": "12:18:58", "dec": "47:18:14"},
    "M107 — Globular Cluster":      {"type": "cluster", "ra": "16:32:32", "dec": "-13:03:11"},
    "M108 — Surfboard Galaxy":      {"type": "galaxy",  "ra": "11:11:31", "dec": "55:40:27"},
    "M109 — Barred Spiral":         {"type": "galaxy",  "ra": "11:57:36", "dec": "53:22:28"},
    "M110 — Dwarf Elliptical":      {"type": "galaxy",  "ra": "0:40:22",  "dec": "41:41:07"},

    # ── Famous NGC objects ────────────────────────────────────────
    "NGC 224 — Andromeda Core":     {"type": "galaxy",  "ra": "0:42:44",  "dec": "41:16:09"},
    "NGC 869 — Double Cluster h":   {"type": "cluster", "ra": "2:19:00",  "dec": "57:08:00"},
    "NGC 884 — Double Cluster Chi": {"type": "cluster", "ra": "2:22:24",  "dec": "57:08:00"},
    "NGC 1499 — California Nebula": {"type": "nebula",  "ra": "4:03:18",  "dec": "36:25:18"},
    "NGC 1976 — Orion Nebula Core": {"type": "nebula",  "ra": "5:35:17",  "dec": "-5:23:28"},
    "NGC 2070 — Tarantula Nebula":  {"type": "nebula",  "ra": "5:38:38",  "dec": "-69:05:42"},
    "NGC 2244 — Rosette Nebula":    {"type": "nebula",  "ra": "6:33:45",  "dec": "4:59:54"},
    "NGC 2392 — Eskimo Nebula":     {"type": "nebula",  "ra": "7:29:11",  "dec": "20:54:42"},
    "NGC 2736 — Pencil Nebula":     {"type": "nebula",  "ra": "9:00:26",  "dec": "-45:57:00"},
    "NGC 3031 — Bode's Galaxy":     {"type": "galaxy",  "ra": "9:55:33",  "dec": "69:03:55"},
    "NGC 3372 — Eta Carinae Neb":   {"type": "nebula",  "ra": "10:43:48", "dec": "-59:52:04"},
    "NGC 3628 — Hamburger Galaxy":  {"type": "galaxy",  "ra": "11:20:17", "dec": "13:35:23"},
    "NGC 4038 — Antennae Galaxy A": {"type": "galaxy",  "ra": "12:01:53", "dec": "-18:52:10"},
    "NGC 4039 — Antennae Galaxy B": {"type": "galaxy",  "ra": "12:01:54", "dec": "-18:53:10"},
    "NGC 4258 — Spiral Galaxy":     {"type": "galaxy",  "ra": "12:18:58", "dec": "47:18:14"},
    "NGC 4565 — Needle Galaxy":     {"type": "galaxy",  "ra": "12:36:21", "dec": "25:59:16"},
    "NGC 4889 — Coma Cluster":      {"type": "galaxy",  "ra": "13:00:08", "dec": "27:58:37"},
    "NGC 5128 — Centaurus A":       {"type": "galaxy",  "ra": "13:25:28", "dec": "-43:01:09"},
    "NGC 5139 — Omega Centauri":    {"type": "cluster", "ra": "13:26:47", "dec": "-47:28:46"},
    "NGC 5194 — Whirlpool Core":    {"type": "galaxy",  "ra": "13:29:53", "dec": "47:11:43"},
    "NGC 5457 — Pinwheel Core":     {"type": "galaxy",  "ra": "14:03:13", "dec": "54:20:56"},
    "NGC 6205 — Hercules Cluster":  {"type": "cluster", "ra": "16:41:41", "dec": "36:27:37"},
    "NGC 6543 — Cat's Eye Nebula":  {"type": "nebula",  "ra": "17:58:33", "dec": "66:37:59"},
    "NGC 6618 — Omega Nebula":      {"type": "nebula",  "ra": "18:20:26", "dec": "-16:10:36"},
    "NGC 6720 — Ring Nebula":       {"type": "nebula",  "ra": "18:53:35", "dec": "33:01:45"},
    "NGC 6853 — Dumbbell Nebula":   {"type": "nebula",  "ra": "19:59:36", "dec": "22:43:16"},
    "NGC 7000 — North America Neb": {"type": "nebula",  "ra": "20:58:48", "dec": "44:19:48"},
    "NGC 7009 — Saturn Nebula":     {"type": "nebula",  "ra": "21:04:11", "dec": "-11:21:49"},
    "NGC 7293 — Helix Nebula":      {"type": "nebula",  "ra": "22:29:38", "dec": "-20:50:14"},
    "NGC 7331 — Spiral Galaxy":     {"type": "galaxy",  "ra": "22:37:04", "dec": "34:24:57"},
    "NGC 7479 — Barred Spiral":     {"type": "galaxy",  "ra": "23:04:57", "dec": "12:19:22"},
    "NGC 7662 — Blue Snowball":     {"type": "nebula",  "ra": "23:25:54", "dec": "42:32:06"},

    # ── Famous named nebulae ──────────────────────────────────────
    "Horsehead Nebula":             {"type": "nebula",  "ra": "5:40:59",  "dec": "-2:27:30"},
    "Pillars of Creation":          {"type": "nebula",  "ra": "18:18:48", "dec": "-13:47:00"},
    "Butterfly Nebula":             {"type": "nebula",  "ra": "17:13:44", "dec": "-37:06:16"},
    "Boomerang Nebula":             {"type": "nebula",  "ra": "12:44:46", "dec": "-54:31:14"},
    "Bubble Nebula":                {"type": "nebula",  "ra": "23:20:48", "dec": "61:12:43"},
    "Flaming Star Nebula":          {"type": "nebula",  "ra": "5:16:00",  "dec": "34:16:00"},
    "Cone Nebula":                  {"type": "nebula",  "ra": "6:41:06",  "dec": "9:53:00"},
    "Witch Head Nebula":            {"type": "nebula",  "ra": "5:06:54",  "dec": "-7:13:48"},
    "Running Man Nebula":           {"type": "nebula",  "ra": "5:35:18",  "dec": "-4:50:00"},
    "Pelican Nebula":               {"type": "nebula",  "ra": "20:50:48", "dec": "44:21:00"},
    "Veil Nebula":                  {"type": "nebula",  "ra": "20:56:24", "dec": "31:43:00"},
    "Cygnus Loop":                  {"type": "nebula",  "ra": "20:51:00", "dec": "30:40:00"},
    "Pac-Man Nebula":               {"type": "nebula",  "ra": "0:52:25",  "dec": "56:33:55"},
    "Heart Nebula":                 {"type": "nebula",  "ra": "2:32:42",  "dec": "61:27:00"},
    "Soul Nebula":                  {"type": "nebula",  "ra": "2:55:00",  "dec": "60:25:00"},
    "Elephant Trunk Nebula":        {"type": "nebula",  "ra": "21:36:00", "dec": "57:30:00"},
    "Wizard Nebula":                {"type": "nebula",  "ra": "0:03:10",  "dec": "67:52:21"},
    "Christmas Tree Cluster":       {"type": "cluster", "ra": "6:41:06",  "dec": "9:53:00"},
    "Thor's Helmet":                {"type": "nebula",  "ra": "7:18:30",  "dec": "-13:13:48"},
    "Seagull Nebula":               {"type": "nebula",  "ra": "7:04:54",  "dec": "-10:27:16"},

    # ── Star clusters ─────────────────────────────────────────────
    "Hyades":                       {"type": "cluster", "ra": "4:27:00",  "dec": "15:52:00"},
    "47 Tucanae":                   {"type": "cluster", "ra": "0:24:05",  "dec": "-72:04:53"},
    "Jewel Box":                    {"type": "cluster", "ra": "12:53:36", "dec": "-60:22:00"},
    "Wild Duck Cluster":            {"type": "cluster", "ra": "18:51:05", "dec": "-6:16:12"},
    "Eta Carinae Cluster":          {"type": "cluster", "ra": "10:44:48", "dec": "-59:52:04"},
    "Trumpler 14":                  {"type": "cluster", "ra": "10:43:57", "dec": "-59:33:00"},
    "Westerlund 1":                 {"type": "cluster", "ra": "16:47:04", "dec": "-45:51:04"},
    "NGC 3603":                     {"type": "cluster", "ra": "11:15:07", "dec": "-61:15:36"},

    # ── Famous stars ──────────────────────────────────────────────
    "Sirius":                       {"type": "star", "ra": "6:45:09",  "dec": "-16:42:58"},
    "Canopus":                      {"type": "star", "ra": "6:23:57",  "dec": "-52:41:44"},
    "Arcturus":                     {"type": "star", "ra": "14:15:40", "dec": "19:10:57"},
    "Vega":                         {"type": "star", "ra": "18:36:56", "dec": "38:47:01"},
    "Capella":                      {"type": "star", "ra": "5:16:41",  "dec": "45:59:53"},
    "Rigel":                        {"type": "star", "ra": "5:14:32",  "dec": "-8:12:06"},
    "Procyon":                      {"type": "star", "ra": "7:39:18",  "dec": "5:13:30"},
    "Betelgeuse":                   {"type": "star", "ra": "5:55:10",  "dec": "7:24:25"},
    "Achernar":                     {"type": "star", "ra": "1:37:43",  "dec": "-57:14:12"},
    "Hadar":                        {"type": "star", "ra": "14:03:49", "dec": "-60:22:23"},
    "Altair":                       {"type": "star", "ra": "19:50:47", "dec": "8:52:06"},
    "Aldebaran":                    {"type": "star", "ra": "4:35:55",  "dec": "16:30:33"},
    "Antares":                      {"type": "star", "ra": "16:29:24", "dec": "-26:25:55"},
    "Spica":                        {"type": "star", "ra": "13:25:12", "dec": "-11:09:41"},
    "Pollux":                       {"type": "star", "ra": "7:45:19",  "dec": "28:01:34"},
    "Fomalhaut":                    {"type": "star", "ra": "22:57:39", "dec": "-29:37:20"},
    "Deneb":                        {"type": "star", "ra": "20:41:26", "dec": "45:16:49"},
    "Mimosa":                       {"type": "star", "ra": "12:47:43", "dec": "-59:41:20"},
    "Polaris":                      {"type": "star", "ra": "2:31:49",  "dec": "89:15:51"},
    "Castor":                       {"type": "star", "ra": "7:34:36",  "dec": "31:53:18"},
    "Acrux":                        {"type": "star", "ra": "12:26:36", "dec": "-63:05:57"},
    "Gacrux":                       {"type": "star", "ra": "12:31:10", "dec": "-57:06:47"},
    "Shaula":                       {"type": "star", "ra": "17:33:37", "dec": "-37:06:14"},
    "Bellatrix":                    {"type": "star", "ra": "5:25:08",  "dec": "6:20:59"},
    "Alnath":                       {"type": "star", "ra": "5:26:17",  "dec": "28:36:27"},
    "Miaplacidus":                  {"type": "star", "ra": "9:13:12",  "dec": "-69:43:02"},
    "Alnilam":                      {"type": "star", "ra": "5:36:13",  "dec": "-1:12:07"},

    # ── Galaxies ──────────────────────────────────────────────────
    "Large Magellanic Cloud":       {"type": "galaxy", "ra": "5:23:34",  "dec": "-69:45:22"},
    "Small Magellanic Cloud":       {"type": "galaxy", "ra": "0:52:45",  "dec": "-72:49:43"},
    "Centaurus A":                  {"type": "galaxy", "ra": "13:25:28", "dec": "-43:01:09"},
    "Sculptor Galaxy":              {"type": "galaxy", "ra": "0:47:33",  "dec": "-25:17:18"},
    "Cartwheel Galaxy":             {"type": "galaxy", "ra": "0:37:41",  "dec": "-33:42:59"},
    "Stephan's Quintet":            {"type": "galaxy", "ra": "22:35:57", "dec": "33:57:36"},
    "Leo Triplet":                  {"type": "galaxy", "ra": "11:20:00", "dec": "13:05:00"},
    "Virgo Cluster Centre":         {"type": "galaxy", "ra": "12:27:00", "dec": "12:43:00"},
    "Fornax Cluster":               {"type": "galaxy", "ra": "3:38:29",  "dec": "-35:27:00"},
    "Coma Cluster":                 {"type": "galaxy", "ra": "12:59:49", "dec": "27:58:50"},

    # ── Special objects ───────────────────────────────────────────
    "Galactic Centre":              {"type": "special", "ra": "17:45:40", "dec": "-29:00:28"},
    "Sagittarius A*":               {"type": "special", "ra": "17:45:40", "dec": "-29:00:28"},
    "Great Attractor":              {"type": "special", "ra": "13:15:00", "dec": "-62:00:00"},
    "Virgo Supercluster Centre":    {"type": "special", "ra": "12:27:00", "dec": "12:43:00"},
}

MIN_ALTITUDE = {
    "planet":       15,
    "dwarf_planet": 15,
    "asteroid":     20,
    "deep_sky":     20,
    "nebula":       20,
    "cluster":      15,
    "galaxy":       20,
    "star":         10,
    "special":      15,
}

def get_ephem_object(name, obj_info):
    if obj_info.get("obj"):
        return obj_info["obj"]()
    fixed        = ephem.FixedBody()
    fixed.name   = name
    fixed._ra    = obj_info["ra"]
    fixed._dec   = obj_info["dec"]
    fixed._epoch = ephem.J2000
    return fixed

def calculate_visibility(lat, lon, object_name, date=None):
    if date is None:
        date = datetime.utcnow()

    obj_info = OBJECTS.get(object_name)
    if not obj_info:
        return None

    obs          = ephem.Observer()
    obs.lat      = str(lat)
    obs.long     = str(lon)
    obs.date     = date.strftime("%Y/%m/%d %H:%M:%S")
    obs.pressure = 0

    target = get_ephem_object(object_name, obj_info)
    target.compute(obs)

    altitude_deg = math.degrees(float(target.alt))
    azimuth_deg  = math.degrees(float(target.az))
    obj_type     = obj_info.get("type", "deep_sky")
    min_alt      = MIN_ALTITUDE.get(obj_type, 15)
    is_visible   = altitude_deg >= min_alt

    try:
        obs.horizon = str(min_alt)
        rise_time   = obs.next_rising(target).datetime()
        set_time    = obs.next_setting(target).datetime()
        hours_up    = (set_time - rise_time).total_seconds() / 3600
        if hours_up < 0:
            hours_up += 24
    except Exception:
        rise_time = None
        set_time  = None
        hours_up  = 0

    if 315 <= azimuth_deg or azimuth_deg < 45:   direction = "N"
    elif 45  <= azimuth_deg < 135:                direction = "E"
    elif 135 <= azimuth_deg < 225:                direction = "S"
    else:                                          direction = "W"

    if altitude_deg >= 60:        visibility_quality = "Excellent"
    elif altitude_deg >= 40:      visibility_quality = "Good"
    elif altitude_deg >= min_alt: visibility_quality = "Marginal"
    else:                         visibility_quality = "Below horizon"

    return {
        "object":             object_name,
        "type":               obj_type,
        "altitude_deg":       round(altitude_deg, 1),
        "azimuth_deg":        round(azimuth_deg, 1),
        "direction":          direction,
        "is_visible":         is_visible,
        "visibility_quality": visibility_quality,
        "rise_time":          rise_time.strftime("%H:%M UTC") if rise_time else "N/A",
        "set_time":           set_time.strftime("%H:%M UTC")  if set_time  else "N/A",
        "hours_visible":      round(max(0, hours_up), 1),
        "min_altitude":       min_alt
    }

def get_best_observatories_for_object(object_name, observatories_df):
    results = []
    for _, row in observatories_df.iterrows():
        try:
            vis = calculate_visibility(
                row["latitude"],
                row["longitude"],
                object_name
            )
            if vis:
                results.append({
                    "observatory":        row["observatory"],
                    "country":            row["country"],
                    "weather_score":      row["observation_score"],
                    "altitude_deg":       vis["altitude_deg"],
                    "direction":          vis["direction"],
                    "is_visible":         vis["is_visible"],
                    "visibility_quality": vis["visibility_quality"],
                    "rise_time":          vis["rise_time"],
                    "set_time":           vis["set_time"],
                    "hours_visible":      vis["hours_visible"],
                })
        except Exception:
            continue

    df = pd.DataFrame(results)
    if df.empty:
        return df

    df["combined_score"] = (
        df["weather_score"] * 0.6 +
        df["altitude_deg"].clip(0, 90) / 90 * 100 * 0.4
    ).round(1)

    return df[df["is_visible"]].sort_values(
        "combined_score", ascending=False
    )

if __name__ == "__main__":
    print(f"\n Total objects loaded: {len(OBJECTS)}\n")
    result = calculate_visibility(19.8207, -155.4681, "M42 — Orion Nebula")
    if result:
        print(f"  Object   : {result['object']}")
        print(f"  Altitude : {result['altitude_deg']}°")
        print(f"  Visible  : {result['is_visible']}")
        print(f"  Quality  : {result['visibility_quality']}\n")