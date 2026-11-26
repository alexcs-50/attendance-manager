# Attendance Manager for Vercel

1. Upload the contents of this folder to a new GitHub repository. Keep app.py, register.html, schema.sql and requirements.txt at its root, with app.js and style.css inside public/.
2. Create a Neon Postgres project. In the Neon SQL Editor run schema.sql against the database/branch you will connect. Copy its pooled database connection string.
3. In Vercel create a new project and import the GitHub repository. Use the Flask preset. Add DATABASE_URL (the Neon connection string) and ADMIN_PASSWORD (choose a strong unique teacher password) to the production environment before deploying.
4. Deploy and open the assigned HTTPS URL. The browser will request a username and password. Sign in as teacher using the password configured for this project.
5. Add two fictional students, mark attendance, save, refresh and check Reports or Download CSV. Records are stored in the selected Neon database.

This edition starts with an empty online roster. Your Mac edition uses a separate SQLite database. Keep credentials in Vercel environment variables. For an isolated demo, connect preview deployments to a separate database branch.
