RBM Textile Costing - Streamlit Cloud Final Version
==================================================

IMPORTANT SECURITY
------------------
1. Do not upload .env or secrets.toml with real keys to GitHub.
2. Put keys only in Streamlit Cloud -> App -> Settings -> Secrets.
3. Because your old Supabase key was visible in screenshots/GitHub, rotate/create a NEW Supabase secret key before final client use.

LOCAL TEST ON WINDOWS
---------------------
1. Extract this ZIP.
2. Open the extracted folder.
3. Open CMD in this folder.
4. Run:

   pip install -r requirements.txt

5. Create folder .streamlit if missing.
6. Copy .streamlit/secrets.toml.example and rename to secrets.toml.
7. Paste your NEW Supabase secret key in secrets.toml.
8. Run:

   streamlit run streamlit_app.py

9. Login:
   username: admin
   password: rbm123

GITHUB UPLOAD
-------------
Upload these files/folders to GitHub:

- streamlit_app.py
- requirements.txt
- README_STEP_BY_STEP.txt

Do NOT upload:
- .streamlit/secrets.toml
- .env

STREAMLIT CLOUD DEPLOY
----------------------
1. Open https://share.streamlit.io/
2. Login with GitHub.
3. New app.
4. Select repository: Siyaram_Textile_Costing or your new Streamlit repo.
5. Main file path:

   streamlit_app.py

6. Advanced settings -> Secrets.
7. Paste:

   SUPABASE_URL = "https://mmzvwlitakluttlnnioh.supabase.co"
   SUPABASE_SECRET_KEY = "PASTE_NEW_SUPABASE_SECRET_KEY_HERE"

8. Deploy.
9. Final URL will open on mobile and desktop.
10. Client can use browser menu -> Add to Home Screen.

FEATURES INCLUDED
-----------------
- Login from Supabase users table
- Permission control
- Cost Sheet
- Cost - Local
- Cost - Export
- Add Sort
- Edit Sort
- Delete Sort
- RM Price Master with dropdowns
- User Management
- Supabase data from sort_master and rm_price_master
- Compact professional UI
