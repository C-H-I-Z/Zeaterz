from flask import Flask, render_template_string

app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOTA — Help</title>

<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

<style>
  :root {
    --navy:    #1a2f5e;
    --blue:    #2e6db4;
    --lblue:   #5ba3d9;
    --cyan:    #4dc8e8;
    --bg:      #eaf3fb;
    --white:   #ffffff;
    --text:    #1a2f5e;
    --muted:   #6b82a8;
    --border:  #c5d8ed;
    --font:    'Montserrat', sans-serif;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    overflow-x: hidden;
  }

  .page {
    min-height: 100vh;
    position: relative;
    display: flex;
    flex-direction: column;
  }

  .wave-bg {
    position: fixed;
    top: 0;
    right: 0;
    width: 55%;
    height: 100vh;
    pointer-events: none;
    z-index: 0;
  }

  header {
    position: relative;
    z-index: 10;
    background: var(--white);
    padding: 16px 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 12px rgba(26,47,94,0.08);
  }

  .logo-wrap {
    display: flex;
    align-items: center;
  }

  .logo-img {
    height: 52px;
    width: auto;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 22px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .nav-links a {
    color: var(--muted);
    text-decoration: none;
  }

  .nav-links a:hover {
    color: var(--blue);
  }

  .tool-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 3px 10px;
    border: 1px solid var(--border);
    border-radius: 3px;
  }

  .content {
    position: relative;
    z-index: 5;
    flex: 1;
    padding: 48px 56px 60px;
  }

  .help-about-layout {
    position: relative;
    width: 100%;
    min-height: 520px;
  }

  .help-about-left {
    width: 620px;
  }

  .page-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--blue);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .page-heading {
    font-size: 36px;
    font-weight: 800;
    color: var(--navy);
    line-height: 1.15;
    margin-bottom: 8px;
    letter-spacing: -0.01em;
  }

  .page-sub {
    font-size: 13px;
    color: var(--muted);
    font-weight: 500;
    margin-bottom: 18px;
  }

  .info-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 28px;
    box-shadow: 0 8px 30px rgba(26,47,94,0.12);
    max-width: 620px;
  }

  .info-card h3 {
    font-size: 15px;
    color: var(--navy);
    margin: 18px 0 8px;
  }

  .info-card p,
  .info-card li {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.7;
    font-weight: 500;
  }

  .info-card ul {
    padding-left: 18px;
  }

  .help-about-image {
    position: absolute;
    top: 25%;
    right: 70px;
    transform: translateY(-50%);
    width: 600px;
  }

  .help-about-image img {
    width: 100%;
    max-width: 600px;
    height: auto;
    object-fit: contain;
  }

  .help-about-medtech {
    position: absolute;
    top: 75%;
    right: 25px;
    transform: translateY(-50%);
    width: 600px;
  }

  .help-about-medtech img {
    width: 100%;
    max-width: 520px;
    height: auto;
    object-fit: contain;
  }

  footer {
    position: relative;
    z-index: 5;
    background: var(--navy);
    padding: 14px 56px;
    text-align: center;
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: auto;
  }
</style>
</head>

<body>

<div class="page">

  <svg class="wave-bg" viewBox="0 0 600 900" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="wv1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#5ba3d9;stop-opacity:0.5"/>
        <stop offset="100%" style="stop-color:#2e6db4;stop-opacity:0.3"/>
      </linearGradient>

      <linearGradient id="wv2" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#4dc8e8;stop-opacity:0.4"/>
        <stop offset="100%" style="stop-color:#5ba3d9;stop-opacity:0.2"/>
      </linearGradient>

      <linearGradient id="wv3" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#7b68ee;stop-opacity:0.3"/>
        <stop offset="100%" style="stop-color:#2e6db4;stop-opacity:0.15"/>
      </linearGradient>
    </defs>

    <path d="M600,0 L600,900 L0,900 Q150,700 300,600 Q450,500 600,300 Z" fill="url(#wv3)" opacity="0.5"/>
    <path d="M600,0 L600,900 L100,900 Q200,750 350,650 Q500,550 600,350 Z" fill="url(#wv1)" opacity="0.6"/>
    <path d="M600,200 Q500,350 400,450 Q300,550 250,700 Q200,800 300,900 L600,900 Z" fill="url(#wv2)" opacity="0.7"/>
  </svg>

  <header>

    <div class="logo-wrap">
      <img class="logo-img"
        src="https://static.wixstatic.com/media/9f2dc8_980147f3f25a4e50a2220ab0bd98dba8~mv2.png/v1/fill/w_129,h_128,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Sig%20logo.png"
        alt="Rallis-Daw Consulting">
    </div>

    <div class="header-right">

      <nav class="nav-links">
        <a href="/">Upload</a>
        <a href="/help">Help</a>
        <a href="/about">About</a>
      </nav>

      <div class="tool-label">
        SOTA — Prototype v0.1
      </div>

    </div>

  </header>

  <div class="content">

    <section id="helpScreen">

      <div class="help-about-layout">

        <div class="help-about-left">

          <div class="page-title">
            User Support
          </div>

          <div class="page-heading">
            Help Center
          </div>

          <div class="page-sub">
            Use these FAQ(s) to understand how SOTA supports requirements
            management for medical device professionals.
          </div>

          <div class="info-card">

            <h3>How to upload a document</h3>

            <ul>
              <li>Go to the Upload screen.</li>
              <li>Drag and drop a PDF, DOCX, or XLSX file into the upload box.</li>
              <li>Click “Extract Requirements” to process the file.</li>
            </ul>

            <h3>Accepted file types</h3>

            <p>
              SOTA currently accepts PDF, DOCX, and XLSX files.
            </p>

            <h3>Manual review warnings</h3>

            <p>
              If a result is marked for manual review, verify it using
              the official regulatory source before relying on it.
            </p>

            <h3>Contact</h3>

            <p>
              91 Avenida Del Mar, Suite 300B San Clemente, CA 92672 USA
            </p>

            <p>
              info@rallis-dawconsulting.com
              Tel: +1 (949) 624-4252
            </p>

          </div>

        </div>

        <div class="help-about-image">
          <img src="/static/official.gif" alt="Compliance Animation">
        </div>

        <div class="help-about-medtech">
          <img src="/static/medtech.avif" alt="Medtech Professionals Image">
        </div>

      </div>

    </section>

  </div>

  <footer>
    &copy; Rallis-Daw Consulting LLC &middot; SOTA Tool &middot; For internal use only
  </footer>

</div>

</body>
</html>
"""

@app.route("/")
def help_page():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(debug=False, port=5000)