"""
ArXiv Categories and Subcategories
Source: https://arxiv.org/category_taxonomy
"""

ARXIV_CATEGORIES = {
    "Physics": {
        "astro-ph": {
            "name": "Astrophysics",
            "subcategories": {
                "astro-ph.CO": "Cosmology and Nongalactic Astrophysics",
                "astro-ph.EP": "Earth and Planetary Astrophysics",
                "astro-ph.GA": "Astrophysics of Galaxies",
                "astro-ph.HE": "High Energy Astrophysical Phenomena",
                "astro-ph.IM": "Instrumentation and Methods for Astrophysics",
                "astro-ph.SR": "Solar and Stellar Astrophysics"
            }
        },
        "cond-mat": {
            "name": "Condensed Matter",
            "subcategories": {
                "cond-mat.dis-nn": "Disordered Systems and Neural Networks",
                "cond-mat.mes-hall": "Mesoscale and Nanoscale Physics",
                "cond-mat.mtrl-sci": "Materials Science",
                "cond-mat.other": "Other Condensed Matter",
                "cond-mat.quant-gas": "Quantum Gases",
                "cond-mat.soft": "Soft Condensed Matter",
                "cond-mat.stat-mech": "Statistical Mechanics",
                "cond-mat.str-el": "Strongly Correlated Electrons",
                "cond-mat.supr-con": "Superconductivity"
            }
        },
        "gr-qc": {
            "name": "General Relativity and Quantum Cosmology",
            "subcategories": {}
        },
        "hep-ex": {
            "name": "High Energy Physics - Experiment",
            "subcategories": {}
        },
        "hep-lat": {
            "name": "High Energy Physics - Lattice",
            "subcategories": {}
        },
        "hep-ph": {
            "name": "High Energy Physics - Phenomenology",
            "subcategories": {}
        },
        "hep-th": {
            "name": "High Energy Physics - Theory",
            "subcategories": {}
        },
        "math-ph": {
            "name": "Mathematical Physics",
            "subcategories": {}
        },
        "nlin": {
            "name": "Nonlinear Sciences",
            "subcategories": {
                "nlin.AO": "Adaptation and Self-Organizing Systems",
                "nlin.CD": "Chaotic Dynamics",
                "nlin.CG": "Cellular Automata and Lattice Gases",
                "nlin.PS": "Pattern Formation and Solitons",
                "nlin.SI": "Exactly Solvable and Integrable Systems"
            }
        },
        "nucl-ex": {
            "name": "Nuclear Experiment",
            "subcategories": {}
        },
        "nucl-th": {
            "name": "Nuclear Theory",
            "subcategories": {}
        },
        "physics": {
            "name": "Physics",
            "subcategories": {
                "physics.acc-ph": "Accelerator Physics",
                "physics.ao-ph": "Atmospheric and Oceanic Physics",
                "physics.app-ph": "Applied Physics",
                "physics.atm-clus": "Atomic and Molecular Clusters",
                "physics.atom-ph": "Atomic Physics",
                "physics.bio-ph": "Biological Physics",
                "physics.chem-ph": "Chemical Physics",
                "physics.class-ph": "Classical Physics",
                "physics.comp-ph": "Computational Physics",
                "physics.data-an": "Data Analysis, Statistics and Probability",
                "physics.ed-ph": "Physics Education",
                "physics.flu-dyn": "Fluid Dynamics",
                "physics.gen-ph": "General Physics",
                "physics.geo-ph": "Geophysics",
                "physics.hist-ph": "History and Philosophy of Physics",
                "physics.ins-det": "Instrumentation and Detectors",
                "physics.med-ph": "Medical Physics",
                "physics.optics": "Optics",
                "physics.plasm-ph": "Plasma Physics",
                "physics.pop-ph": "Popular Physics",
                "physics.soc-ph": "Physics and Society",
                "physics.space-ph": "Space Physics"
            }
        },
        "quant-ph": {
            "name": "Quantum Physics",
            "subcategories": {}
        }
    },
    "Mathematics": {
        "math": {
            "name": "Mathematics",
            "subcategories": {
                "math.AG": "Algebraic Geometry",
                "math.AT": "Algebraic Topology",
                "math.AP": "Analysis of PDEs",
                "math.CT": "Category Theory",
                "math.CA": "Classical Analysis and ODEs",
                "math.CO": "Combinatorics",
                "math.AC": "Commutative Algebra",
                "math.CV": "Complex Variables",
                "math.DG": "Differential Geometry",
                "math.DS": "Dynamical Systems",
                "math.FA": "Functional Analysis",
                "math.GM": "General Mathematics",
                "math.GN": "General Topology",
                "math.GT": "Geometric Topology",
                "math.GR": "Group Theory",
                "math.HO": "History and Overview",
                "math.IT": "Information Theory",
                "math.KT": "K-Theory and Homology",
                "math.LO": "Logic",
                "math.MP": "Mathematical Physics",
                "math.MG": "Metric Geometry",
                "math.NT": "Number Theory",
                "math.NA": "Numerical Analysis",
                "math.OA": "Operator Algebras",
                "math.OC": "Optimization and Control",
                "math.PR": "Probability",
                "math.QA": "Quantum Algebra",
                "math.RT": "Representation Theory",
                "math.RA": "Rings and Algebras",
                "math.SP": "Spectral Theory",
                "math.ST": "Statistics Theory",
                "math.SG": "Symplectic Geometry"
            }
        }
    },
    "Computer Science": {
        "cs": {
            "name": "Computer Science",
            "subcategories": {
                "cs.AI": "Artificial Intelligence",
                "cs.AR": "Hardware Architecture",
                "cs.CC": "Computational Complexity",
                "cs.CE": "Computational Engineering",
                "cs.CG": "Computational Geometry",
                "cs.CL": "Computation and Language",
                "cs.CR": "Cryptography and Security",
                "cs.CV": "Computer Vision and Pattern Recognition",
                "cs.CY": "Computers and Society",
                "cs.DB": "Databases",
                "cs.DC": "Distributed Computing",
                "cs.DL": "Digital Libraries",
                "cs.DM": "Discrete Mathematics",
                "cs.DS": "Data Structures and Algorithms",
                "cs.ET": "Emerging Technologies",
                "cs.FL": "Formal Languages and Automata Theory",
                "cs.GL": "General Literature",
                "cs.GR": "Graphics",
                "cs.GT": "Computer Science and Game Theory",
                "cs.HC": "Human-Computer Interaction",
                "cs.IR": "Information Retrieval",
                "cs.IT": "Information Theory",
                "cs.LG": "Machine Learning",
                "cs.LO": "Logic in Computer Science",
                "cs.MA": "Multiagent Systems",
                "cs.MM": "Multimedia",
                "cs.MS": "Mathematical Software",
                "cs.NA": "Numerical Analysis",
                "cs.NE": "Neural and Evolutionary Computing",
                "cs.NI": "Networking and Internet Architecture",
                "cs.OH": "Other Computer Science",
                "cs.OS": "Operating Systems",
                "cs.PF": "Performance",
                "cs.PL": "Programming Languages",
                "cs.RO": "Robotics",
                "cs.SC": "Symbolic Computation",
                "cs.SD": "Sound",
                "cs.SE": "Software Engineering",
                "cs.SI": "Social and Information Networks",
                "cs.SY": "Systems and Control"
            }
        }
    },
    "Quantitative Biology": {
        "q-bio": {
            "name": "Quantitative Biology",
            "subcategories": {
                "q-bio.BM": "Biomolecules",
                "q-bio.CB": "Cell Behavior",
                "q-bio.GN": "Genomics",
                "q-bio.MN": "Molecular Networks",
                "q-bio.NC": "Neurons and Cognition",
                "q-bio.OT": "Other Quantitative Biology",
                "q-bio.PE": "Populations and Evolution",
                "q-bio.QM": "Quantitative Methods",
                "q-bio.SC": "Subcellular Processes",
                "q-bio.TO": "Tissues and Organs"
            }
        }
    },
    "Quantitative Finance": {
        "q-fin": {
            "name": "Quantitative Finance",
            "subcategories": {
                "q-fin.CP": "Computational Finance",
                "q-fin.EC": "Economics",
                "q-fin.GN": "General Finance",
                "q-fin.MF": "Mathematical Finance",
                "q-fin.PM": "Portfolio Management",
                "q-fin.PR": "Pricing of Securities",
                "q-fin.RM": "Risk Management",
                "q-fin.ST": "Statistical Finance",
                "q-fin.TR": "Trading and Market Microstructure"
            }
        }
    },
    "Statistics": {
        "stat": {
            "name": "Statistics",
            "subcategories": {
                "stat.AP": "Applications",
                "stat.CO": "Computation",
                "stat.ME": "Methodology",
                "stat.ML": "Machine Learning",
                "stat.OT": "Other Statistics",
                "stat.TH": "Theory"
            }
        }
    },
    "Economics": {
        "econ": {
            "name": "Economics",
            "subcategories": {
                "econ.EM": "Econometrics",
                "econ.GN": "General Economics",
                "econ.TH": "Theory"
            }
        }
    },
    "Electrical Engineering and Systems Science": {
        "eess": {
            "name": "Electrical Engineering and Systems Science",
            "subcategories": {
                "eess.AS": "Audio and Speech Processing",
                "eess.IV": "Image and Video Processing",
                "eess.SP": "Signal Processing",
                "eess.SY": "Systems and Control"
            }
        }
    }
}