# Flight Logbook

A Django-based flight logbook application for tracking flight time, currency, and license progress. Supports local data entry via Django admin and static site deployment to GitHub Pages.
Purely for myself, if you like it you could clone it and run it yourself but the GitHub pages link is my data.
Most of this file is Claude btw, I don't write like this...

## Features

- **Flight Tracking**: Record all flight details including times, landings, routes, and notes
- **Currency Monitoring**: Automatic tracking of FAR 61.57(a) passenger currency (day/night)
- **License Progress**: Track progress toward Commercial Pilot (FAR 61.129) and Instrument Rating (FAR 61.65d)
- **Medical Certificate**: Monitor medical certificate expiration
- **Charts & Statistics**: Visual dashboards with monthly activity, cumulative time, and aircraft breakdown
- **Leaderboards**: Track passengers and instructors by flight count

## Architecture

This is a hybrid application:
- **Local Development**: Django admin for data entry (single-user mode)
- **Static Deployment**: Exported HTML/JSON for GitHub Pages hosting
- **Client-side Currency**: JavaScript recalculates currency status in real-time on the static site

## Local Setup

1. **Install dependencies**:
   ```bash
   pip install django
   ```

2. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Create a pilot** (required for single-user mode):
   ```bash
   python manage.py createsuperuser
   # Then add a Pilot record via admin with pk=1
   ```

4. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

5. **Access the application**:
   - Dashboard: http://localhost:8000/
   - Admin: http://localhost:8000/admin/

## Static Site Deployment

### Export Static Site

Run the export command to generate the static site:

```bash
python manage.py export_static
```

This creates a `static_site/` directory with:
- `index.html` - Dashboard page
- `logbook.html` - Logbook table
- `data/flights.json` - All flight records
- `data/stats.json` - Dashboard statistics
- `data/charts.json` - Chart data
- `data/leaderboards.json` - Passenger/instructor leaderboards
- `.nojekyll` - Prevents Jekyll processing on GitHub Pages

### Deploy to GitHub Pages

1. **Configure GitHub Pages**:
   - Go to your repository settings
   - Under "Pages", set source to "Deploy from a branch"
   - Select branch: `main` (or your default branch)
   - Select folder: `/static_site`
   - Save

2. **Deploy using the automated script**:
   ```bash
   ./deploy.sh
   ```

   Or manually:
   ```bash
   python manage.py export_static
   git add static_site/
   git commit -m "Update flight data"
   git push origin main
   ```

3. **Access your site**:
   - Your site will be available at: `https://<username>.github.io/<repository-name>/`
   - Updates appear within 1-2 minutes after pushing

### Workflow

1. **Add flights locally**: Use Django admin at http://localhost:8000/admin/
2. **Export static site**: Run `python manage.py export_static`
3. **Deploy**: Run `./deploy.sh` or manually commit and push
4. **View online**: Check your GitHub Pages site

## Key Files

- **Models**: `flights/models.py`, `pilots/models.py`, `planes/models.py`, etc.
- **Views**: `flights/views/dashboard_views.py`
- **Templates**: `flights/templates/flights/`
- **Statistics**: `flights/utils/statistics.py`, `flights/utils/currency_calculator.py`
- **Export Command**: `flights/management/commands/export_static.py`
- **Deploy Script**: `deploy.sh`

## Data Privacy

The database (`db.sqlite3`) is excluded from version control and stays on your local machine. Only the exported HTML and JSON data (in `static_site/`) is committed to the repository.

**Important**: GitHub Pages sites are public by default. If you want privacy:
- Use a private repository (requires GitHub Pro for GitHub Pages)
- Redact sensitive information (passenger names, routes) before exporting
- Consider alternative hosting with authentication

## Technical Details

- **Django Version**: Compatible with Django 4.x+
- **Database**: SQLite (local only)
- **Frontend**: Bootstrap 5 + Chart.js (loaded from CDN)
- **Currency Calculations**: Client-side JavaScript recalculates from JSON data
- **Single-User Mode**: Hardcoded to `Pilot.objects.get(pk=1)`

## License

This project is for personal use.