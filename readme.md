# Setting Up the Streamlit App

## Steps to Set Up the Project

### 1. Install Python
- Download and install Python from [python.org](https://www.python.org/).
- Ensure to check the option **Add Python to PATH** during installation.

### 2. Create and Activate Virtual Environment in Windows

1. Open the terminal and navigate to your project folder.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   ```bash
   .venv\Scripts\activate
   ```

### 3. Install Required Packages
- Install all packages listed in `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

### 4. Create Configuration Files

1. Create a new folder named `.streamlit`:
   ```bash
   mkdir .streamlit
   ```

2. Inside `.streamlit`, create a file named `secrets.toml`:
   ```bash
   echo > .streamlit\secrets.toml
   ```

3. Add the following line to `secrets.toml`:
   ```toml
   GROQ_API_KEY = "api key"
   ```

### 5. Run the Streamlit App
- Execute the following command in the terminal:
  ```bash
  streamlit run app.py
  ```
- Your app will open automatically in the browser at **http://localhost:8501**.

---

## Author
**Vignesh**
