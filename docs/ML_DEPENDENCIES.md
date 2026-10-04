# TwinBean Phase 3 ML dependencies

## Authorization and scope

On 2026-10-04, the project user explicitly authorized installation of these
official packages for the Phase 3 synthetic AKI research prototype.  This
record identifies the packages and their resolved versions; it does not make
arbitrary serialized model files trustworthy.  D-10 still requires a
controlled SHA-256 checksum barrier before any joblib or pickle
deserialization.

| Package | Exact pin | Official PyPI project | Official documentation/source | Resolved locally |
| --- | --- | --- | --- | --- |
| pandas | `3.0.6` | https://pypi.org/project/pandas/ | https://pandas.pydata.org/docs/ | `3.0.6` |
| scikit-learn | `1.9.1` | https://pypi.org/project/scikit-learn/ | https://scikit-learn.org/stable/ | `1.9.1` |
| xgboost | `3.4.1` | https://pypi.org/project/xgboost/ | https://xgboost.readthedocs.io/ | `3.4.1` |
| shap | `0.52.0` | https://pypi.org/project/shap/ | https://shap.readthedocs.io/ | `0.52.0` |

## Repeatable verification

From the repository root, install the editable backend with its development
test dependencies:

```powershell
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
backend\.venv\Scripts\python.exe -c "import subprocess,sys; from importlib.metadata import version; expected={'pandas':'3.0.6','scikit-learn':'1.9.1','xgboost':'3.4.1','shap':'0.52.0'}; assert {name:version(name) for name in expected} == expected; subprocess.run([sys.executable,'-m','pip','check'],check=True)"
```

Any dependency upgrade requires a new compatibility review and a new model
artifact/schema version before an artifact can be used for inference.
