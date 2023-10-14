from datetime import datetime, timezone, timedelta
from tqdm import tqdm
import uuid


from functools import wraps
import os
from flask import request, render_template, session
from itsdangerous import URLSafeTimedSerializer
import constants.plans as plans
from flask_mail import Message


from flask_restx import Api, Resource, fields


from flask import request
import pyrebase
from core.interrogator_chatgpt import image_to_prompt, get_title_desc_seo


# from core.generator import generate_image_ai_premium
import jwt
from .models import (
    db,
    Users,
    JWTTokenBlocklist,
    UserImages,
    mail,
    FreeUserLog,
    photos,
)
from .config import BaseConfig

import redis
import uuid
import firebase_admin
from firebase_admin import credentials, storage
from pathlib import Path

# Initialize Firebase app with credentials
if not firebase_admin._apps:
    path = Path("core", "conf.json")
    cred = credentials.Certificate(path)
    firebase_admin.initialize_app(cred)
    bucket = storage.bucket(name="long-plexus-376814.appspot.com")


rs = redis.Redis(host="localhost", port=6379, db=0)
rest_api = Api(version="1.0", title="Image Scribe API")

image_model = rest_api.model("Image", {"photo": fields.String})


from PIL import Image


s = URLSafeTimedSerializer("Thisisasecret!")

"""
    Flask-Restx models for api request and response data
"""


signup_model = rest_api.model(
    "SignUpModel",
    {
        "username": fields.String(required=True, min_length=2, max_length=32),
        "email": fields.String(required=True, min_length=4, max_length=64),
        "password": fields.String(required=True, min_length=4, max_length=16),
    },
)


login_model = rest_api.model(
    "LoginModel",
    {
        "email": fields.String(required=True, min_length=4, max_length=64),
        "password": fields.String(required=True, min_length=4, max_length=16),
    },
)


user_edit_model = rest_api.model(
    "UserEditModel",
    {
        "userID": fields.String(required=True, min_length=1, max_length=32),
        "username": fields.String(required=True, min_length=2, max_length=32),
        "email": fields.String(required=True, min_length=4, max_length=64),
    },
)

sub_edit_model = rest_api.model(
    "SubEditModel",
    {
        "userID": fields.String(required=True, min_length=1, max_length=32),
        "subsription_type": fields.String(required=True, min_length=2, max_length=32),
    },
)
image_url_model = rest_api.model(
    "ImageURIModel",
    {
        "userID": fields.String(required=True, min_length=1, max_length=32),
        "url": fields.String(required=True, min_length=2),
    },
)

"""
   Helper function for JWT token required
"""


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        if "authorization" in request.headers:
            token = request.headers["authorization"]

        if not token:
            return {"success": False, "msg": "Valid JWT token is missing"}, 400

        data = jwt.decode(token, BaseConfig.SECRET_KEY, algorithms=["HS256"])
        current_user = Users.get_by_email(data["email"])

        if not current_user:
            return {
                "success": False,
                "msg": "Sorry. Wrong auth token. This user does not exist.",
            }, 400

        token_expired = (
            db.session.query(JWTTokenBlocklist.id).filter_by(jwt_token=token).scalar()
        )

        if token_expired is not None:
            return {"success": False, "msg": "Token revoked."}, 400

        if not current_user.check_jwt_auth_active():
            return {"success": False, "msg": "Token expired."}, 400

        # except:
        #     return {"success": False, "msg": "Token is invalid"}, 400

        return f(current_user, *args, **kwargs)

    return decorator


"""
    Flask-Restx routes
"""


@rest_api.route("/api/upload")
class FileUpload(Resource):
    @rest_api.expect(image_model)
    @token_required
    def post(self, current_user):
        files = request.files.getlist("photo")

        user_id = request.form.get("user_id")

        file_names_image = []
        file_names_thumbnails = []
        pic_urls = []
        thumnbails_urls = []
        pic_names = []

        total_iterations = len(files)
        progress_bar = tqdm(total=total_iterations, desc="Processing", unit="iteration")

        i = 0
        my_urls = []
        for file in files:
            x = photos.save(file)
            filepath = os.path.join(os.getcwd(), "images", x)

            file_names_image.append(str(filepath))
            pic_names.append(x)

            thumbnail = Image.open(filepath)
            thumbnail.thumbnail(tuple(x / 2 for x in thumbnail.size))

            filepath_thumbnail = os.path.join(os.getcwd(), "thumbnail", x)
            thumbnail.save(str(filepath_thumbnail))
            file_names_thumbnails.append(str(filepath_thumbnail))

            # Destination path of file in Firebase Storage
            destination_path_img = f"images/{x}"

            # Create a blob object with the file data
            blob_img = bucket.blob(destination_path_img)
            blob_img.upload_from_filename(filepath)

            # storage.child(f"images/{x}").put(str(filepath))
            destination_path_thumb = f"thumbnails/{x}"
            blob_thumb = bucket.blob(destination_path_thumb)
            blob_thumb.upload_from_filename(filepath_thumbnail)
            # storage.child(f"thumbnails/{x}-thumbnail").put(str(filepath_thumbnail))

            # pic_url = storage.child(f"images/{x}").get_url(None)
            # thumbnail_url = storage.child(f"thumbnails/{x}-thumbnail").get_url(None)
            pic_url = blob_img.generate_signed_url(expiration=timedelta(days=30))
            thumbnail_url = blob_thumb.generate_signed_url(
                expiration=timedelta(days=30)
            )

            new_dict = {}
            new_dict["image_url"] = pic_url
            new_dict["thumbnail_url"] = thumbnail_url
            new_dict["pic_names"] = x
            my_urls.append(new_dict)
            pic_urls.append(pic_url)
            thumnbails_urls.append(thumbnail_url)

            progress_bar.update(1)
            print("progress", i)
            i += 1
        for file in file_names_image:
            os.remove(file)
        for file in file_names_thumbnails:
            os.remove(file)

        progress_bar.close()

        return {"status": "success", "urls": my_urls}


from urllib.request import urlretrieve
from PIL import Image
import pandas as pd
import random


@rest_api.route("/api/process")
class Process(Resource):
    @token_required
    def post(self, current_user):
        data = request.get_json()
        user_id = data["user_id"]
        category = data["category"]
        text_length = data["text_length"]  # description length
        text_style = data["text_style"]
        title_length = data["title_length"]  # short, medium, long
        seo_hashtags_length = data["seo_hash_length"]  # 5,10,15
        img_urls = data["img_urls"]
        brand = data["brand"]
        print(img_urls)
        print(img_urls[0])
        urls = []
        thumbnails = []
        pic_names = []
        n = len(img_urls)
        for x, y in enumerate(img_urls):
            urls.append(y["image_url"])
        for x, y in enumerate(img_urls):
            thumbnails.append(y["thumbnail_url"])
        for x, y in enumerate(img_urls):
            pic_names.append(y["pic_names"])

        total_iterations = len(urls)
        progress_bar = tqdm(total=total_iterations, desc="Processing", unit="iteration")
        if text_length.lower() == "short":
            length_of_desc = "10-20"
        elif text_length.lower() == "medium":
            length_of_desc = "20-40"
        elif text_length.lower() == "long":
            length_of_desc = "40-60"

        if title_length.lower() == "short":
            length_of_title = "2-3"
        elif title_length.lower() == "medium":
            length_of_title = "4-6"
        elif title_length.lower() == "long":
            length_of_title = "6-12"

        mega_response = []
        for i, (url, thumbnail, name) in enumerate(zip(urls, thumbnails, pic_names)):
            my_dict = {}
            file_path = os.path.join("./temp", f"m{i}.png")
            urlretrieve(url, file_path)
            # img = Image.open(file_path)
            prompt = image_to_prompt(file_path)
            try:
                prompt = prompt.split(",")[0]
            except:
                pass
            # paoss above prompt to gpt model
            # get
            title, description, seo_hashtag = get_title_desc_seo(
                style_input=text_style,
                text_input=prompt,
                hashtags_len=seo_hashtags_length,
                length_of_title=length_of_title,
                length_of_description=length_of_desc,
                brand_name=brand,
                product_style=category,
            )

            my_dict["filename"] = name
            my_dict["title"] = title
            my_dict["description"] = description
            my_dict["seo_hashtags"] = seo_hashtag

            mega_response.append(my_dict)

            images = UserImages(
                user_id=user_id,
                url=url,
                thumbnail=thumbnail,
                filename=name,
                title=title,
                description=description,
                seo_hashtags=seo_hashtag,
                brand=brand,
                category=category,
            )
            images.save()

            progress_bar.update(1)
            print("progress", i)

            i += 1

        rd = {"response": mega_response}
        nameee = f"{str(uuid.uuid1())}.csv"

        df = pd.DataFrame(rd["response"])
        df.to_csv(nameee, index=False)
        destination_path_csv = f"csv/{nameee}"
        blob_csv = bucket.blob(destination_path_csv)
        blob_csv.upload_from_filename(nameee)

        csv_url = blob_csv.generate_signed_url(expiration=timedelta(days=30))
        nameee = f"{str(uuid.uuid1())}.txt"
        with open(f"{nameee}", "w") as f:
            for col in df.columns:
                f.write(col + "\n")  # Write column name on a new line
                f.write(df[col].str.cat(sep="\n") + "\n\n")
        destination_path_txt = f"txt/{nameee}"
        blob_txt = bucket.blob(destination_path_txt)
        blob_txt.upload_from_filename(nameee)

        txt_url = blob_txt.generate_signed_url(expiration=timedelta(days=30))

        if user_id:
            self.update_images(n)
            self.save()

        return {"response": mega_response, "csv_url": csv_url, "txt_url": txt_url}


@rest_api.route("/api/verifyLimit")
class Verify(Resource):
    def post(self):
        date = datetime.now().date().strftime(r"%Y-%m-%d")
        if request.environ.get("HTTP_X_FORWARDED_FOR") is None:
            ip = request.environ["REMOTE_ADDR"]
        else:
            ip = request.environ["HTTP_X_FORWARDED_FOR"]
        check_user = FreeUserLog(ip_address=ip, visit_date=date).get_by_ip_address(
            ip=ip, date=date
        )

        if len(check_user) == 0:
            new_user = FreeUserLog(ip_address=ip, visit_date=date)
            new_user.save()
            new_user = new_user.get_by_ip_address(ip=ip, date=date)

            return {
                "success": True,
                "allowed_images": new_user[-1].get_allowed_images(),
            }, 200
        else:
            return {
                "success": True,
                "allowed_images": check_user[-1].get_allowed_images(),
            }, 200


@rest_api.route("/api/users/register")
class Register(Resource):
    """
    Creates a new user by taking 'signup_model' input
    """

    @rest_api.expect(signup_model, validate=True)
    def post(self):
        req_data = request.get_json()

        _username = req_data.get("username")
        _email = req_data.get("email")
        _password = req_data.get("password")

        user_exists = Users.get_by_email(_email)
        if user_exists:
            return {"success": False, "msg": "Email already taken"}, 400

        new_user = Users(username=_username, email=_email)

        new_user.set_password(_password)
        new_user.save()
        # msg = Message(
        #     "Welcome to generateimage.ai",
        #     sender="support@generateimage.ai",
        #     recipients=[_email],
        # )

        # msg.html = render_template("welcome_email.html")

        # mail.send(msg)

        return {
            "success": True,
            "userID": new_user.id,
            "msg": "The user was successfully registered",
        }, 200


@rest_api.route("/api/users/login")
class Login(Resource):
    """
    Login user by taking 'login_model' input and return JWT token
    """

    @rest_api.expect(login_model, validate=True)
    def post(self):
        req_data = request.get_json()

        _email = req_data.get("email")
        _password = req_data.get("password")

        user_exists = Users.get_by_email(_email)

        if not user_exists:
            return {"success": False, "msg": "This email does not exist."}, 400

        if not user_exists.check_password(_password):
            return {"success": False, "msg": "Wrong credentials."}, 400

        # create access token uwing JWT
        token = jwt.encode(
            {"email": _email, "exp": datetime.utcnow() + timedelta(days=30)},
            BaseConfig.SECRET_KEY,
        )

        user_exists.set_jwt_auth_active(True)
        user_exists.save()

        return {"success": True, "token": token, "user": user_exists.toJSON()}, 200


@rest_api.route("/api/users/updateSub")
class updateSub(Resource):
    @rest_api.expect(sub_edit_model)
    @token_required
    def post(self, current_user):
        req_data = request.get_json()
        plan_type = req_data["plan_type"]  # credit/sub
        sub_tier = req_data["sub_tier"]  # basic/pro
        _id = req_data["id"]
        plan_name = req_data["plan_name"]
        user_exists = Users.get_by_id(_id)
        if plan_name:
            # self.update_renewal_date()
            if plan_type.upper() == "CREDIT_BASED":
                self.update_plan_type(plans.PLAN_TYPE.CREDIT_BASED.name)
                if sub_tier.upper() == "BASIC":
                    self.update_sub_tier(plans.SUBSCRIPTION_TIER.BASIC.name)

                    if plan_name.upper() == "STARTER":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_BASIC.STARTER.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_BASIC.STARTER.value
                        )
                    if plan_name.upper() == "GROWTH":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_BASIC.GROWTH.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_BASIC.GROWTH.value
                        )

                    if plan_name.upper() == "EXPANSION":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_BASIC.EXPANSION.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_BASIC.EXPANSION.value
                        )

                    if plan_name.upper() == "ENTERPRISE":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_BASIC.ENTERPRISE.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_BASIC.ENTERPRISE.value
                        )
                if sub_tier.upper() == "PRO":
                    self.update_sub_tier(plans.SUBSCRIPTION_TIER.PRO.name)

                    if plan_name.upper() == "STARTER":
                        self.update_plan_name(plans.CREDIT_BASED_PLANS_PRO.STARTER.name)
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_PRO.STARTER.value
                        )
                    if plan_name.upper() == "GROWTH":
                        self.update_plan_name(plans.CREDIT_BASED_PLANS_PRO.GROWTH.name)
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_PRO.GROWTH.value
                        )

                    if plan_name.upper() == "EXPANSION":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_PRO.EXPANSION.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_PRO.EXPANSION.value
                        )

                    if plan_name.upper() == "ENTERPRISE":
                        self.update_plan_name(
                            plans.CREDIT_BASED_PLANS_PRO.ENTERPRISE.name
                        )
                        self.update_allowed_images(
                            plans.CREDIT_BASED_PLANS_PRO.ENTERPRISE.value
                        )

            if plan_type.upper() == "SUBSCRIPTION_BASED":
                self.update_plan_type(plans.PLAN_TYPE.SUBSCRIPTION_BASED.name)
                if sub_tier.upper() == "BASIC":
                    self.update_sub_tier(plans.SUBSCRIPTION_TIER.BASIC.name)
                    if plan_name.upper() == "BASIC_ELITE":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_ELITE.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_ELITE.value
                        )
                        self.update_renewal_date(26)
                        self.update_duration(plans.Duration.SIX_MONTHS.name)
                    if plan_name.upper() == "BASIC_ESSENTIALS":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_ESSENTIALS.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_ESSENTIALS.value
                        )
                        self.update_renewal_date(13)
                        self.update_duration(plans.Duration.THREE_MONTHS.name)

                    if plan_name.upper() == "BASIC_PRO":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_PRO.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_PRO.value
                        )
                        self.update_renewal_date(13)
                        self.update_duration(plans.Duration.THREE_MONTHS.name)
                    if plan_name.upper() == "BASIC_UNLIMITED":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_UNLIMITED.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_BASIC.BASIC_UNLIMITED.value
                        )
                        self.update_renewal_date(26)
                        self.update_duration(plans.Duration.SIX_MONTHS.name)
                if sub_tier.upper() == "PRO":
                    self.update_sub_tier(plans.SUBSCRIPTION_TIER.PRO.name)
                    if plan_name.upper() == "PRO_ELITE":
                        self.update_plan_name(plans.SUB_BASED_PLANS_PRO.PRO_ELITE.name)
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_PRO.PRO_ELITE.value
                        )
                        self.update_renewal_date(26)
                        self.update_duration(plans.Duration.SIX_MONTHS.name)
                    if plan_name.upper() == "PRO_ESSENTIALS":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_PRO.PRO_ESSENTIALS.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_PRO.PRO_ESSENTIALS.value
                        )
                        self.update_renewal_date(13)
                        self.update_duration(plans.Duration.THREE_MONTHS.name)

                    if plan_name.upper() == "PRO_PLUS":
                        self.update_plan_name(plans.SUB_BASED_PLANS_PRO.PRO_PLUS.name)
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_PRO.PRO_PLUS.value
                        )
                        self.update_renewal_date(13)
                        self.update_duration(plans.Duration.THREE_MONTHS.name)

                    if plan_name.upper() == "PRO_UNLIMITED":
                        self.update_plan_name(
                            plans.SUB_BASED_PLANS_PRO.PRO_UNLIMITED.name
                        )
                        self.update_allowed_images(
                            plans.SUB_BASED_PLANS_PRO.PRO_UNLIMITED.value
                        )
                        self.update_renewal_date(26)
                        self.update_duration(plans.Duration.SIX_MONTHS.name)
        self.save()
        return {"success": True, "user": user_exists.toJSON()}, 200


import time

import random


@rest_api.route("/api/users/email/forgetPassword")
class VerifyEmail(Resource):
    def post(self):
        req_data = request.get_json()

        email = req_data["email"]
        print(email)
        user_exists = Users.get_by_email(email=email)
        if user_exists:
            otp = str(random.randint(1000, 9999))
            msg = Message(
                "We've recieved password change request",
                sender="ashhadahsan@gmail.com",
                recipients=[email],
            )
            msg.html = render_template("reset_password.html", OTP=otp)

            mail.send(msg)
            # session["otp_obj"] = {"email": email, "otp": otp}

            rs.set("email", email)
            rs.set("otp", otp)

            rs.expire("otp", time=30)
            return {"success": True}, 200
        else:
            return {"succes": False, "msg": "user does not exist"}, 400


@rest_api.route("/api/users/email/verifyOtp")
class ResetPassword(Resource):
    def post(self):
        data = request.get_json()
        otp_now = str(data["otp"])
        email = data["email"]
        print(type(rs.get("otp").decode("utf-8")))

        if rs.get("email").decode("utf-8") == email:
            print("email ok")
            try:
                if rs.get("otp").decode("utf-8") == otp_now:
                    return {"success": True}, 200
                else:
                    session.pop("otp", None)
                    session.pop("email", None)
                    return {"succes": False, "msg": "Invalid OTP"}, 401
            except AttributeError:
                session.pop("otp", None)
                session.pop("email", None)
                return {"succes": False, "msg": "Expired OTP"}, 402

        else:
            return {"succes": False, "msg": "Wrong email"}, 400


@rest_api.route("/api/users/email/changePassword")
class ChangePassword(Resource):
    @rest_api.expect(user_edit_model)
    def post(self):
        req_data = request.get_json()
        email = req_data["email"]
        user_exists = Users.get_by_email(email=email)
        new_password = req_data["new_password"]
        if user_exists:
            user_exists.update_password(new_password)
            user_exists.save()
        return {"success": True, "user": user_exists.toJSON()}, 200


@rest_api.route("/api/users/getHistory")
class GetAllImages(Resource):
    @rest_api.expect(image_url_model)
    @token_required
    def get(self, current_user):
        id = request.form.get("user_id")
        images = UserImages()

        # id = req_data["id"]
        obj = images.get_all_images(id=id)

        images = [x.url for x in obj]
        thumbnails = [x.thumbnail for x in obj]
        title = [x.title for x in obj]
        description = [x.description for x in obj]
        seo_hashtags = [x.seo_hashtags for x in obj]
        return {
            "urls": images,
            "thumbnail": thumbnails,
            "title": title,
            "description": description,
            "seo_hashtags": seo_hashtags,
        }, 200


@rest_api.route("/api/users/ResetPassword")
class ResetPassword(Resource):
    @rest_api.expect(user_edit_model)
    @token_required
    def post(self, current_user):
        req_data = request.get_json()
        id = req_data["id"]
        old = req_data["old"]
        new = req_data["new"]

        if self.check_password(old):
            self.update_password(new)
            self.save()

            return {"sucess": True}, 200
        else:
            return {"success": False}, 401
