from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, PyPDF2, docx

# ---------- Flask App Setup ----------
app = Flask(__name__)
app.secret_key = "careerhub_secret"

# ---------- Paths & Upload Folder ----------
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------- Database Setup ----------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'careerhub.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    def __repr__(self):
        return f"<User {self.name}>"

class Company(db.Model):
    company_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    role_title = db.Column(db.String(150), nullable=False)
    company_logo = db.Column(db.String(255))
    website = db.Column(db.String(255))
    location = db.Column(db.String(150))
    description = db.Column(db.Text)
    def __repr__(self):
        return f"<Company {self.company_name} - {self.role_title}>"

# ---------- Resume Helpers ----------
def extract_text(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

def analyze_resume(text):
    score = 50
    strengths, improvements, skill_gaps, ai_tips = [], [], [], []
    sections = {"Technical Skills": 0, "Soft Skills": 0, "Formatting & ATS Match": 70}
    text_lower = text.lower()

    # Detect Domain
    if any(word in text_lower for word in ["accounting","finance","bcom","tax","gst","tally"]):
        category = "commerce"
    elif any(word in text_lower for word in ["marketing","seo","social media","branding"]):
        category = "marketing"
    elif any(word in text_lower for word in ["python","java","developer","software","html"]):
        category = "it"
    else:
        category = "general"

    # Domain Skill Map
    skill_map = {
        "it": {
            "python":"Python experience",
            "java":"Java experience",
            "sql":"SQL / Database experience",
            "javascript":"JavaScript",
            "react":"React.js",
            "html":"HTML",
            "css":"CSS",
            "machine learning":"Machine Learning",
            "deep learning":"Deep Learning"
        },
        "commerce":{
            "accounting":"Accounting knowledge",
            "gst":"GST filing knowledge",
            "tally":"Tally ERP",
            "finance":"Financial management",
            "tax":"Taxation knowledge",
            "excel":"Advanced Excel",
            "audit":"Auditing knowledge"
        },
        "marketing":{
            "seo":"SEO skills",
            "social media":"Social Media Marketing",
            "google ads":"Google Ads",
            "content marketing":"Content strategy",
            "branding":"Branding skills"
        },
        "general":{
            "communication":"Strong communication",
            "leadership":"Leadership skills",
            "team":"Team collaboration",
            "project":"Project experience"
        }
    }

    selected_skills = skill_map.get(category, skill_map["general"])

    # Skill Analysis
    for word, desc in selected_skills.items():
        if word in text_lower:
            score += 5
            strengths.append(desc)
            sections["Technical Skills"] += 15
        else:
            improvements.append(f"Consider adding {desc}")  
            skill_gaps.append(word)                          
            ai_tips.append(f"Include {desc} in your resume to improve your profile strength.")

    # Soft Skills Detection
    for soft in ["communication","leadership","team"]:
        if soft in text_lower:
            sections["Soft Skills"] += 30

    score = min(score, 100)
    sections = {k: min(v, 100) for k, v in sections.items()}

    # --------- Career Insights (Multiple Role Recommendations) ---------
    career_insights = []

    if category == "it":
        career_insights = [
            "Software Developer",
            "Python Developer",
            "Frontend Developer",
            "Data Analyst"
        ]

        if "machine learning" in text_lower or "deep learning" in text_lower:
            career_insights.append("AI / ML Developer")

    elif category == "commerce":
        career_insights = [
            "Accountant",
            "Financial Analyst",
            "Tax Consultant",
            "Auditor"
        ]

    elif category == "marketing":
        career_insights = [
            "Digital Marketing Executive",
            "SEO Specialist",
            "Social Media Manager",
            "Brand Strategist"
        ]

    else:
        career_insights = [
            "Business Analyst",
            "Operations Executive",
            "Project Coordinator"
        ]

    return {
        "score": score,
        "strengths": strengths,
        "improvements": improvements,
        "skill_gaps": skill_gaps,
        "ai_tips": ai_tips,
        "section_scores": sections,
        "career_insights": career_insights,
        "detected_category": category
    }

# ---------- Roles Database ----------
roles_db = [
    {"title":"Python Developer","keywords":["python","django","flask"],"description":"Design and build applications using Python."},
    {"title":"Frontend Developer","keywords":["javascript","react","css","html"],"description":"Design and develop user interfaces."},
    {"title":"Java Backend Developer","keywords":["java","spring","sql"],"description":"Develop server-side logic with Java."},
    {"title":"Data Analyst","keywords":["sql","excel","python","tableau"],"description":"Analyze and interpret data."},
    {"title":"Data Scientist","keywords":["python","machine learning","pandas"],"description":"Analyze data and build predictive models."},
    {"title":"AI/ML Developer","keywords":["machine learning","deep learning","tensorflow","pytorch"],"description":"Build AI applications and models."},
    {"title":"Marketing Manager","keywords":["seo","branding","social media"],"description":"Plan and execute marketing campaigns."},
    {"title":"Accountant","keywords":["accounting","finance","gst","tally"],"description":"Manage financial records and transactions."},
    {"title":"MBA Business Analyst","keywords":["business analysis","finance","strategy"],"description":"Perform business research and analysis."}
]


# ---------- Sample Company Data ----------
def populate_companies():
    """Populate top companies per role into the Company table"""
    if Company.query.first():
        print("✅ Companies already populated in the database.")
        return

    top_companies = {
        "Python Developer": [
            {"company_name":"Google","website":"https://careers.google.com/jobs/results/","location":"Global"},
            {"company_name":"Microsoft","website":"https://careers.microsoft.com/","location":"Global"},
            {"company_name":"Amazon","website":"https://www.amazon.jobs/en/","location":"Global"}
        ],
        "Frontend Developer": [
            {"company_name":"Google","website":"https://careers.google.com/jobs/results/","location":"Global"},
            {"company_name":"Microsoft","website":"https://careers.microsoft.com/","location":"Global"},
            {"company_name":"Amazon","website":"https://www.amazon.jobs/en/","location":"Global"}
        ],
        "Java Backend Developer": [
            {"company_name":"Amazon","website":"https://www.amazon.jobs/en/","location":"Global"},
            {"company_name":"IBM","website":"https://www.ibm.com/careers","location":"Global"},
            {"company_name":"Accenture","website":"https://www.accenture.com/us-en/careers","location":"Global"}
        ],
        "Data Analyst": [
            {"company_name":"IBM","website":"https://www.ibm.com/careers","location":"Global"},
            {"company_name":"Accenture","website":"https://www.accenture.com/us-en/careers","location":"Global"},
            {"company_name":"Deloitte","website":"https://www2.deloitte.com/careers","location":"Global"}
        ],
        "Data Scientist": [
            {"company_name":"IBM","website":"https://www.ibm.com/careers","location":"Global"},
            {"company_name":"Microsoft","website":"https://careers.microsoft.com/","location":"Global"},
            {"company_name":"Amazon","website":"https://www.amazon.jobs/en/","location":"Global"}
        ],
        "AI/ML Developer": [
            {"company_name":"Google AI","website":"https://ai.google/research/","location":"Global"},
            {"company_name":"Microsoft AI","website":"https://www.microsoft.com/en-us/ai","location":"Global"},
            {"company_name":"Amazon AI","website":"https://aws.amazon.com/machine-learning/","location":"Global"}
        ],
        "Marketing Manager": [
            {"company_name":"HubSpot","website":"https://www.hubspot.com/careers","location":"Global"},
            {"company_name":"Google","website":"https://careers.google.com/jobs/results/","location":"Global"},
            {"company_name":"Meta","website":"https://www.metacareers.com/","location":"Global"}
        ],
        "Accountant": [
            {"company_name":"Deloitte","website":"https://www2.deloitte.com/careers","location":"Global"},
            {"company_name":"KPMG","website":"https://home.kpmg/careers","location":"Global"},
            {"company_name":"PwC","website":"https://www.pwc.com/careers","location":"Global"}
        ],
        "MBA Business Analyst": [
            {"company_name":"McKinsey & Company","website":"https://www.mckinsey.com/careers","location":"Global"},
            {"company_name":"Boston Consulting Group","website":"https://www.bcg.com/careers","location":"Global"},
            {"company_name":"Goldman Sachs","website":"https://www.goldmansachs.com/careers/","location":"Global"}
        ]
    }

    for role, companies in top_companies.items():
        for c in companies:
            company = Company(
                company_name=c["company_name"],
                role_title=role,
                website=c["website"],
                location=c["location"]
            )
            db.session.add(company)

    db.session.commit()
    print("✅ Top companies populated for all roles!")

# ---------- Routes: Home / Auth ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("⚠️ Email already exists!", "danger")
            return redirect(url_for("register"))
        user = User(name=name,email=email,password=password)
        db.session.add(user)
        db.session.commit()
        session["user"] = name
        flash("✅ Registration successful!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email,password=password).first()
        if user:
            session["user"] = user.name
            flash("✅ Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid email or password!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("✅ Logged out successfully!", "success")
    return redirect(url_for("home"))

# ---------- Dashboard ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("⚠️ Please login first.", "warning")
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

# ---------- Resume Upload / Result ----------
@app.route("/resume")
def resume():
    if "user" not in session:
        flash("⚠️ Please login first.", "warning")
        return redirect(url_for("login"))

    # Clear any old resume data when opening the page
    session.pop("resume_analysis", None)

    return render_template("resume.html")

@app.route("/upload", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        flash("⚠️ No file selected!", "danger")
        return redirect(url_for("resume"))

    file = request.files["resume"]
    if file.filename == "":
        flash("⚠️ Please upload a valid file.", "danger")
        return redirect(url_for("resume"))

    if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(".docx")):
        flash("⚠️ Only PDF or DOCX resumes are allowed.", "danger")
        return redirect(url_for("resume"))

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    text = extract_text(file_path)
    result = analyze_resume(text)

    # Save results in session
    session["resume_analysis"] = result

    # Don't flash "role not found" here; just handle it in resume_result if needed
    return redirect(url_for("resume_result"))


@app.route("/resume_result")
def resume_result():
    resume_data = session.get("resume_analysis")
    if not resume_data:
        flash("⚠️ Please analyze a resume first.", "warning")
        return redirect(url_for("resume"))
    return render_template(
        "resume_result.html",
        score=resume_data.get("score",0),
        section_scores=resume_data.get("section_scores",{}),
        strengths=resume_data.get("strengths",[]),
        improvements=resume_data.get("improvements",[]),
        skill_gaps=resume_data.get("skill_gaps",[]),
        ai_tips=resume_data.get("ai_tips",[]),
        career_insights=resume_data.get("career_insights",[])
    )

# ---------- Job Matching ----------
def generate_role_matches(skills):
    skills_lower = [s.lower() for s in skills]
    matched_roles = []
    for role in roles_db:
        match_count = sum(1 for k in role["keywords"] if any(k in sk.lower() for sk in skills_lower))
        if match_count > 0:
            missing_skills = [k for k in role["keywords"] if all(k not in sk.lower() for sk in skills_lower)]
            matched_roles.append({
                "title": role["title"],
                "description": role["description"],
                "match_score": int((match_count / len(role["keywords"])) * 100),
                "missing_skills": missing_skills
            })
    matched_roles.sort(key=lambda x: x["match_score"], reverse=True)
    return matched_roles

@app.route("/job_matching")
def job_matching():
    if "user" not in session:
        flash("⚠️ Please login first.", "warning")
        return redirect(url_for("login"))

    resume_data = session.get("resume_analysis")
    if not resume_data:
        flash("⚠️ Please analyze a resume first.", "warning")
        return redirect(url_for("resume"))

    skills = resume_data.get("strengths", [])
    role_matches = generate_role_matches(skills)
    career_insights = resume_data.get("career_insights", [])

    # ✅ NEW: Find highest match safely
    highest_match = None
    if role_matches:
        highest_match = max(role_matches, key=lambda x: x["match_score"])

    return render_template(
        "job_matching.html",
        skills=skills,
        career_insights=career_insights,
        role_matches=role_matches,
        highest_match=highest_match
    )

# ---------- Job Details ----------
@app.route("/job/<role>")
def job_detail(role):
    if "user" not in session:
        flash("⚠️ Please login first.", "warning")
        return redirect(url_for("login"))

    resume_data = session.get("resume_analysis")
    if not resume_data:
        flash("⚠️ Please analyze a resume first.", "warning")
        return redirect(url_for("resume"))

    user_skills = resume_data.get("strengths", [])
    role_name = role.replace("_", " ")

    # Find role info from roles_db
    role_info = next((r for r in roles_db if r["title"].lower() == role_name.lower()), None)
    if not role_info:
        flash("⚠️ Role not found.", "danger")
        return redirect(url_for("job_matching"))

    matched_skills = [s for s in user_skills if any(k.lower() in s.lower() for k in role_info["keywords"])]
    missing_skills = [k for k in role_info["keywords"] if all(k.lower() not in s.lower() for s in user_skills)]
    skill_match_percent = int((len(matched_skills) / len(role_info["keywords"])) * 100)
    
    # Career readiness index
    career_readiness = int(skill_match_percent * 0.7 + 30)
    if career_readiness >= 80:
        interview_probability = "High"
    elif career_readiness >= 60:
        interview_probability = "Medium"
    else:
        interview_probability = "Low"

    # Resume improvement suggestions
    resume_actions = [f"Add {skill} to your resume for better match." for skill in missing_skills]

    return render_template(
        "job_detail.html",
        role=role_name.title(),
        description=role_info["description"],
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        readiness=career_readiness,
        probability=interview_probability,
        resume_actions=resume_actions
    )


@app.route("/company_hiring/<role>")
def company_hiring(role):
    if "user" not in session:
        flash("⚠️ Please login first.", "warning")
        return redirect(url_for("login"))

    # Convert URL‑friendly role back to readable
    role_name = role.replace("_", " ")

    # Fetch companies from DB that match the role_title
    companies = Company.query.filter(Company.role_title.ilike(f"%{role_name}%")).all()

    if not companies:
        flash(f"⚠️ No companies found for '{role_name}' currently.", "warning")
        companies = []

    # Real certification links by role
    role_certifications = {
        "Python Developer": [
            {"name":"Python for Everybody (Coursera)","link":"https://www.coursera.org/specializations/python"},
            {"name":"Complete Python Bootcamp (Udemy)","link":"https://www.udemy.com/course/complete-python-bootcamp/"},
            {"name":"Google IT Automation with Python (Coursera)","link":"https://www.coursera.org/professional-certificates/google-it-automation"}
        ],
        "Frontend Developer": [
            {"name":"HTML, CSS, and JavaScript for Web Developers (Coursera)","link":"https://www.coursera.org/learn/html-css-javascript-for-web-developers"},
            {"name":"The Complete 2025 Web Development Bootcamp (Udemy)","link":"https://www.udemy.com/course/the-complete-web-development-bootcamp/"},
            {"name":"Meta Front-End Developer Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/meta-front-end-developer"}
        ],
        "Java Backend Developer": [
            {"name":"Java Programming and Software Engineering Fundamentals (Coursera)","link":"https://www.coursera.org/specializations/java-programming"},
            {"name":"Spring & Hibernate for Beginners (Udemy)","link":"https://www.udemy.com/course/spring-hibernate-tutorial/"},
            {"name":"Oracle Java Certification (Oracle)","link":"https://education.oracle.com/java-certification"}
        ],
        "Data Analyst": [
            {"name":"Google Data Analytics Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/google-data-analytics"},
            {"name":"IBM Data Analyst Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/ibm-data-analyst"},
            {"name":"Excel to MySQL: Analytic Techniques (Coursera)","link":"https://www.coursera.org/specializations/excel-mysql"}
        ],
        "Data Scientist": [
            {"name":"IBM Data Science Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/ibm-data-science"},
            {"name":"Machine Learning by Andrew Ng (Coursera)","link":"https://www.coursera.org/learn/machine-learning"},
            {"name":"Deep Learning Specialization (Coursera)","link":"https://www.coursera.org/specializations/deep-learning"}
        ],
        "AI/ML Developer": [
            {"name":"Deep Learning Specialization (Coursera)","link":"https://www.coursera.org/specializations/deep-learning"},
            {"name":"TensorFlow Developer Certificate","link":"https://www.tensorflow.org/certificate"},
            {"name":"AI For Everyone (Coursera)","link":"https://www.coursera.org/learn/ai-for-everyone"}
        ],
        "Marketing Manager": [
            {"name":"Digital Marketing Specialization (Coursera)","link":"https://www.coursera.org/specializations/digital-marketing"},
            {"name":"Google Digital Marketing & E‑Commerce Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/google-digital-marketing-ecommerce"},
            {"name":"Meta Social Media Marketing Professional Certificate (Coursera)","link":"https://www.coursera.org/professional-certificates/meta-social-media-marketing"}
        ],
        "Accountant": [
            {"name":"Introduction to Financial Accounting (Coursera)","link":"https://www.coursera.org/learn/wharton-accounting"},
            {"name":"Google Data Analytics (Coursera)","link":"https://www.coursera.org/professional-certificates/google-data-analytics"},
            {"name":"Excel Skills for Business (Coursera)","link":"https://www.coursera.org/specializations/excel"}
        ],
        "Business Analyst": [
            {"name":"Business Analytics Specialization (Coursera)","link":"https://www.coursera.org/specializations/business-analytics"},
            {"name":"Business Analyst Professional Certificate (Google)","link":"https://www.coursera.org/professional-certificates/google-business-analytics"},
            {"name":"SQL for Data Science (Coursera)","link":"https://www.coursera.org/learn/sql-for-data-science"}
        ]
    }

    guidance = {
        "certifications": role_certifications.get(role_name, []),
        "skills": [],       # You can add role-specific skills lists here
        "keywords": []
    }

    return render_template(
        "company_hiring.html",
        role=role_name,
        companies=companies,
        guidance=guidance
    )
# ---------- Initialize Database ----------
with app.app_context():
    db.create_all()           # Create tables if not exist

    # ⚡ Clear old companies and repopulate sample companies
    Company.query.delete()
    db.session.commit()
    populate_companies()

    print("✅ Database initialized and sample companies populated!")

# ---------- Run Server ----------
if __name__ == "__main__":
    app.run(debug=True)
