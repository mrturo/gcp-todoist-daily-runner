# SECURITY.md

## Vulnerabilidades ignoradas en Trivy

Este proyecto ignora los siguientes CVEs en `.trivyignore` porque:
- Son reportados únicamente en dependencias internas (vendored) de `setuptools/_vendor`.
- La aplicación **no usa** esas versiones vulnerables en tiempo de ejecución.
- Las versiones seguras están instaladas globalmente y son las que realmente utiliza el entorno Python.
- No hay forma de eliminar estos falsos positivos mientras setuptools incluya vendors vulnerables en su código fuente.

### CVEs ignorados
- CVE-2026-23949 (jaraco.context)
- CVE-2026-0994  (protobuf)
- CVE-2026-24049 (wheel)

#### Justificación
- Trivy escanea todos los archivos `.dist-info`, incluyendo los de vendor internos de setuptools.
- El entorno principal de Python usa las versiones seguras forzadas en `requirements.txt` y el `Dockerfile`.
- No hay riesgo real para la aplicación ni para el entorno de ejecución.

#### Referencias
- [Trivy false positives with vendored dependencies](https://github.com/aquasecurity/trivy/discussions/3076)
- [Python setuptools/_vendor issue](https://github.com/pypa/setuptools/issues/3772)

---

Si en el futuro setuptools elimina o actualiza estos vendors, se podrá quitar la excepción del `.trivyignore`.
