import nltk
import pafy
import pymysql
import io,random
import pandas as pd
import base64,random
import time,datetime
from PIL import Image
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from window_create import website
import plotly.express as px
from streamlit_tags import st_tags
import os
import tensorflow as tf
import numpy as np
from tensorflow import keras
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams
import spacy
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
from Courses import *

# resume_score = keras.models.load_model('model.pkl',compile=False)
# nltk.download('stopwords')
# spacy.load('en_core_web_sm')
def fetch_yt_video(link):
    video = pafy.new(link)
    return video.title

def get_table_download_link(df,filename,text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh,caching=True,check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()

    # close open handles
    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="800" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course


connection = pymysql.connect(host='localhost',user='root',password='',db='sra')
cursor = connection.cursor()


def data_base_creator():
        # Create the DB
    db_sql = """CREATE DATABASE IF NOT EXISTS SRA;"""
    cursor.execute(db_sql)

    # Create table
    DB_table_name = 'user_data'
    table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                     Name varchar(100) NOT NULL,
                     Email_ID VARCHAR(50) NOT NULL,
                     resume_score VARCHAR(8) NOT NULL,
                     Timestamp VARCHAR(50) NOT NULL,
                     Page_no VARCHAR(5) NOT NULL,
                     Predicted_Field VARCHAR(25) NOT NULL,
                     User_level VARCHAR(30) NOT NULL,
                     Actual_skills VARCHAR(300) NOT NULL,
                     Recommended_skills VARCHAR(300) NOT NULL,
                     Recommended_courses VARCHAR(600) NOT NULL,
                     PRIMARY KEY (ID));
                    """
    cursor.execute(table_sql)


def insert_data(name,email,res_score,timestamp,no_of_pages,reco_field,cand_level,skills,recommended_skills,courses):
    DB_table_name = 'user_data'
    insert_sql = "insert into " + DB_table_name + """
    values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (name, email, str(res_score), timestamp,str(no_of_pages), reco_field, cand_level, skills,recommended_skills,courses)
    cursor.execute(insert_sql, rec_values)
    connection.commit()


st.set_page_config(
   page_title="Resume Screening",
   layout="wide",
   
)
def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

header_html = "<img src='data:image/jpg;base64,{}' class='img-fluid'>".format(img_to_bytes("about.jpg"))




# Machine Learning Part Training And Test Result
# ===============================================================================================================
# Import Libraries 
import fitz
import numpy as np
import pandas as pd
# SKLEARN Imports...
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.linear_model import SGDClassifier
# ===============================================================================================================
def train_test_sgd_classifier():
    # Train and test algorithm
    df = pd.read_csv('job_desc_csv_fixed_url.csv')
    X_train, X_test, y_train, y_test = train_test_split(df.job_descriptions, df.search_term, random_state=0)

    count_vect = CountVectorizer(stop_words='english')
    X_train_counts = count_vect.fit_transform(X_train)

    tfidf_transformer = TfidfTransformer()
    X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)

    clf = SGDClassifier(loss='hinge', penalty='l1', alpha=1e-3, random_state=42, max_iter=5, tol=None)
    clf.fit(X_train_tfidf, y_train)

    preds = clf.predict(count_vect.transform(X_test))
    accuracy = np.mean(preds==np.array(y_test))

    return clf, count_vect, accuracy

def Convert_Pdf_To_Text(pdf_url):
    with fitz.open(pdf_url) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

def predict_resume(resume_text):
    # Run predict on trained algorithm
    text_as_series = pd.Series(resume_text)
    clf, count_vect, _ = train_test_sgd_classifier()
    prediction = clf.predict(count_vect.transform(text_as_series))
    return prediction[0]

# =======================================================================================================================





def run():
    website()
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.title("Resume Screening")
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
   

    data_base_creator()
   
    if choice == 'Normal User':
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:
            save_image_path = './Uploaded_Resumes/'+pdf_file.name
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            resume_data = ResumeParser(save_image_path).get_extracted_data()
            if resume_data:
                
                resume_text = pdf_reader(save_image_path)
                st.header("Resume Analysis")
                st.success("Hello "+ resume_data['name'])
                st.subheader("Your Basic info")
                try:
                    st.text('Name: '        + resume_data['name'])
                    st.text('Email: '       + resume_data['email'])
                    if resume_data['mobile_number']:
                        st.text('Contact: '     + resume_data['mobile_number'])
                    else:
                        st.text('Contact: '     + resume_data['phone_number'])
                    st.text('Resume pages: '+ str(resume_data['no_of_pages']))
                except:
                    pass
                cand_level = ''

                if resume_data['no_of_pages'] == 1:
                    cand_level = "Fresher"
                    st.markdown( '''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''',unsafe_allow_html=True)
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',unsafe_allow_html=True)
                elif resume_data['no_of_pages'] >=3:
                    cand_level = "Experienced"
                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',unsafe_allow_html=True)

                st.subheader("Skills Recommendation💡")
                ## Skill shows
                keywords = st_tags(label='Skills that you have',
                text='See our skills recommendation', value=resume_data['skills'],key = '1')

                ##  recommendation
                ds_keyword      = ['tensorflow','keras','pytorch','machine learning','deep Learning','flask','streamlit']
                web_keyword     = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress','javascript', 'angular js', 'c#', 'flask']
                android_keyword = ['android','android development','flutter','kotlin','xml','kivy']
                ios_keyword     = ['ios','ios development','swift','cocoa','cocoa touch','xcode']
                uiux_keyword    = ['ux','adobe xd','figma','zeplin','balsamiq','ui','prototyping','wireframes','storyframes','adobe photoshop','photoshop','editing','adobe illustrator','illustrator','adobe after effects','after effects','adobe premier pro','premier pro','adobe indesign','indesign','wireframe','solid','grasp','user research','user experience']

                recommended_skills = []
                reco_field = ''
                rec_course = ''
                cv = Convert_Pdf_To_Text(save_image_path)
                
                st.success(f"** Our analysis says you are looking for {predict_resume(cv)} Jobs.")
                recommended_skills = ['Data Visualization','Predictive Analysis','Statistical Modeling','Data Mining','Clustering & Classification','Data Analytics','Quantitative Analysis','Web Scraping','ML Algorithms','Keras','Pytorch','Probability','Scikit-learn','Tensorflow',"Flask",'Streamlit']
                recommended_keywords = st_tags(label='Recommended skills for you.',
                text='Recommended skills generated from System',value=recommended_skills,key = '2')
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                rec_course = course_recommender(ds_course)
                ## Courses recommendation
                # for i in resume_data['skills']:
                #     ## Data science recommendation
                #     if i.lower() in ds_keyword:
                #         # print(i.lower())
                       
                #         st.success("** Our analysis says you are looking for Data Science Jobs.")
                #         recommended_skills = ['Data Visualization','Predictive Analysis','Statistical Modeling','Data Mining','Clustering & Classification','Data Analytics','Quantitative Analysis','Web Scraping','ML Algorithms','Keras','Pytorch','Probability','Scikit-learn','Tensorflow',"Flask",'Streamlit']
                #         recommended_keywords = st_tags(label='Recommended skills for you.',
                #         text='Recommended skills generated from System',value=recommended_skills,key = '2')
                #         st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                #         rec_course = course_recommender(ds_course)
                #         break

                #     ## Web development recommendation
                #     elif i.lower() in web_keyword:
                #         # print(i.lower())
                #         reco_field = 'Web Development'
                #         st.success("** Our analysis says you are looking for Web Development Jobs.")
                #         recommended_skills = ['React','Django','Node JS','React JS','php','laravel','Magento','wordpress','Javascript','Angular JS','c#','Flask','SDK']
                #         recommended_keywords = st_tags(label='Recommended skills for you.',
                #         text='Recommended skills generated from System',value=recommended_skills,key = '3')
                #         st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                #         rec_course = course_recommender(web_course)
                #         break

                #     ## Android App Development
                #     elif i.lower() in android_keyword:
                #         print(i.lower())
                #         reco_field = 'Android Development'
                #         st.success("Our analysis says you are looking for Android App Development Jobs")
                #         recommended_skills = ['Android','Android development','Flutter','Kotlin','XML','Java','Kivy','GIT','SDK','SQLite']
                #         recommended_keywords = st_tags(label='Recommended skills for you.',
                #         text='Recommended skills generated from System',value=recommended_skills,key = '4')
                #         st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                #         rec_course = course_recommender(android_course)
                #         break

                #     ## IOS App Development
                #     elif i.lower() in ios_keyword:
                #         print(i.lower())
                #         reco_field = 'IOS Development'
                #         st.success("** Our analysis says you are looking for IOS App Development Jobs")
                #         recommended_skills = ['IOS','IOS Development','Swift','Cocoa','Cocoa Touch','Xcode','Objective-C','SQLite','Plist','StoreKit',"UI-Kit",'AV Foundation','Auto-Layout']
                #         recommended_keywords = st_tags(label='Recommended skills for you.',
                #         text='Recommended skills generated from System',value=recommended_skills,key = '5')
                #         st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                #         rec_course = course_recommender(ios_course)
                #         break

                #     ## Ui-UX Recommendation
                #     elif i.lower() in uiux_keyword:
                #         print(i.lower())
                #         reco_field = 'UI-UX Development'
                #         st.success("Our analysis says you are looking for UI-UX Development Jobs.")
                #         recommended_skills = ['UI','User Experience','Adobe XD','Figma','Zeplin','Balsamiq','Prototyping','Wireframes','Storyframes','Adobe Photoshop','Editing','Illustrator','After Effects','Premier Pro','Indesign','Wireframe','Solid','Grasp','User Research']
                #         recommended_keywords = st_tags(label='Recommended skills for you.',
                #         text='Recommended skills generated from System',value=recommended_skills,key = '6')
                #         st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''',unsafe_allow_html=True)
                #         rec_course = course_recommender(uiux_course)
                #         break

                # #
                ## Insert into table
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date+'_'+cur_time)

                ### Resume writing recommendation
                st.subheader("Resume Tips & Ideas💡")
                resume_score = 0
                if 'Objective' in resume_text:
                    resume_score = resume_score+20
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add your career objective, it will give your career intension to the Recruiters.</h4>''',unsafe_allow_html=True)

                if 'Declaration'  in resume_text:
                    resume_score = resume_score + 20
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Delcaration✍/h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''',unsafe_allow_html=True)

                if 'Hobbies' or 'Interests'in resume_text:
                    resume_score = resume_score + 20
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies⚽</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Hobbies⚽. It will show your persnality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',unsafe_allow_html=True)

                if 'Achievements' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements🏅 </h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Achievements🏅. It will show that you are capable for the required position.</h4>''',unsafe_allow_html=True)

                if 'Projects' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects👨‍💻 </h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Projects👨‍💻. It will show that you have done work related the required position or not.</h4>''',unsafe_allow_html=True)

                st.subheader("Resume Score📝")
                st.markdown(
                    """
                    <style>
                        .stProgress > div > div > div > div {
                            background-color: #d73b5c;
                        }
                        footer{
                            display : none;
                        }
                    </style>""",
                    unsafe_allow_html=True,)
                my_bar = st.progress(0)
                score = 0
                for percent_complete in range(resume_score):
                    score +=1
                    time.sleep(0.1)
                    my_bar.progress(percent_complete + 1)
                st.success('Your Resume Writing Score: ' + str(score))
                st.warning("Note: This score is calculated based on the content that you have added in your Resume.")
                st.balloons()

                insert_data(resume_data['name'], resume_data['email'], str(resume_score), timestamp,
                              str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
                              str(recommended_skills), str(rec_course))


                ## Resume writing video
                st.header("Bonus Video for Resume Writing Tips")
                resume_vid = random.choice(resume_videos)
                res_vid_title = fetch_yt_video(resume_vid)
                st.subheader('"'+res_vid_title+'"')
                st.video(resume_vid)

                ## Interview Preparation Video
                st.header("Bonus Video for Interview Tips")
                interview_vid = random.choice(interview_videos)
                int_vid_title = fetch_yt_video(interview_vid)
                st.subheader('"' + int_vid_title + '"')
                st.video(interview_vid)

                connection.commit()
            else:
                st.error('Something went wrong..')
    else:
        ## Admin Side
        st.success('Welcome to Admin Side')

        ad_user = st.text_input("Username : ")
        ad_password = st.text_input("Password : ", type='password')
        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'admin':
                st.success(f"Welcome {ad_user}")
                # Display Data
                cursor.execute('''SELECT*FROM user_data''')
                data = cursor.fetchall()
                st.header("User's Data")
                df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                                 'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills',
                                                 'Recommended Course'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df,'User_Data.csv','Download Report'), unsafe_allow_html=True)
                ## Admin Side Data
                query = 'select * from user_data;'
                plot_data = pd.read_sql(query, connection)

                ## Pie chart for predicted field recommendations
                labels = plot_data.Predicted_Field.unique()
                values = plot_data.Predicted_Field.value_counts()
                st.subheader("Pie-Chart for Predicted Field Recommendations")
                fig = px.pie(df, values=values, names=labels, title='Predicted Field according to the Skills')
                st.plotly_chart(fig)

                ### Pie chart for User's Experienced Level
                labels = plot_data.User_level.unique()
                values = plot_data.User_level.value_counts()
                st.subheader("Pie-Chart for User's Experienced Level")
                fig = px.pie(df, values=values, names=labels, title="Pie-Chart for User's Experienced Level")
                st.plotly_chart(fig)


            else:
                st.error("Wrong ID & Password Provided")

run()
