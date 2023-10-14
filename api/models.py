# -*- encoding: utf-8 -*-


from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import constants.plans as plans

db = SQLAlchemy()
mail = Mail()
from flask_uploads import IMAGES, UploadSet, configure_uploads

photos = UploadSet("photos", IMAGES)


class Admin(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(32), nullable=False)
    password = db.Column(db.Text())
    jwt_auth_active = db.Column(db.Boolean())

    def save(self):
        db.session.add(self)
        db.session.commit()

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def check_jwt_auth_active(self):
        return self.jwt_auth_active

    def set_jwt_auth_active(self, set_status):
        self.jwt_auth_active = set_status

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    def toDICT(self):
        cls_dict = {}
        cls_dict["_id"] = self.id
        cls_dict["username"] = self.username

        return cls_dict

    def toJSON(self):
        return self.toDICT()


class Prompts(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    prompts = db.Column(db.Text())
    username = db.Column(db.Text())

    def save(self):
        db.session.add(self)
        db.session.commit()


class Users(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.Text())
    jwt_auth_active = db.Column(db.Boolean())
    date_joined = db.Column(db.DateTime(), default=datetime.utcnow)

    plan_type = db.Column(db.Text(), default=plans.PLAN_TYPE.FREE.name)  # done
    sub_tier = db.Column(db.Text(), default=plans.SUBSCRIPTION_TIER.FREE.name)
    plan_name = db.Column(db.Text(), default=plans.CREDIT_BASED_PLANS_BASIC.FREE.name)

    duration = db.Column(db.Text(), default=plans.Duration.NONE.name)

    allowed_images = db.Column(db.Integer(), default=15)
    subscription_date = db.Column(db.DateTime(), default=datetime.utcnow)
    subscription_renewal_date = db.Column(db.DateTime(), default=datetime.utcnow())

    def __repr__(self):
        return f"User {self.username}"

    def update_plan_type(self, plan_type):
        self.plan_type = plan_type

    def update_sub_tier(self, sub_teir):
        self.sub_tier = sub_teir

    def update_plan_name(self, sub_name):
        self.plan_name = sub_name

    def save(self):
        db.session.add(self)
        db.session.commit()

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def update_allowed_images(self, new_limit):
        self.allowed_images = new_limit

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def update_email(self, new_email):
        self.email = new_email

    def update_images(self, generated):
        current_images = self.allowed_images
        self.allowed_images = current_images - generated

    def get_images(self):
        return self.allowed_images

    def update_duration(self, duration):
        self.duration = duration

    def update_renewal_date(self, week):
        current_date = self.subscription_renewal_date
        self.subscription_renewal_date = current_date + timedelta(weeks=week)

    def update_username(self, new_username):
        self.username = new_username

    def update_password(self, new_password):
        self.password = generate_password_hash(new_password)

    def check_jwt_auth_active(self):
        return self.jwt_auth_active

    def set_jwt_auth_active(self, set_status):
        self.jwt_auth_active = set_status

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    def toDICT(self):
        cls_dict = {}
        cls_dict["_id"] = self.id
        cls_dict["username"] = self.username
        cls_dict["email"] = self.email

        cls_dict["plan_type"] = self.plan_type
        cls_dict["plan_name"] = self.plan_name
        cls_dict["sub_tier"] = self.sub_tier

        cls_dict["duration"] = str(self.duration)
        cls_dict["allowed_images"] = self.allowed_images
        cls_dict["subscription_renewal_date"] = str(self.subscription_renewal_date)

        return cls_dict

    def toJSON(self):
        return self.toDICT()


class FreeUserLog(db.Model):
    user_id = db.Column(db.Integer(), primary_key=True)
    ip_address = db.Column(db.Text())
    allowed_images = db.Column(db.Integer(), default=4)
    visit_date = db.Column(db.Text())

    def save(self):
        db.session.add(self)
        db.session.commit()

    def set_ip(self, ip):
        self.ip_address = ip

    def get_allowed_images(self):
        return self.allowed_images

    # def get_allowed_images(self):
    #     return self.allowed_images

    def get_ip(self):
        return self.ip_address

    def set_allowed_images(self, images):
        self.allowed_images = images

    @classmethod
    def get_by_ip_address(cls, ip, date):
        return cls.query.filter_by(ip_address=ip, visit_date=date).all()

    def toDICT(self):
        cls_dict = {}
        cls_dict["ip_address"] = self.ip_address
        cls_dict["allowed_images"] = self.allowed_images
        cls_dict["date"] = str(self.visit_date)

        return cls_dict

    def toJSON(self):
        return self.toDICT()


class UserImages(db.Model):
    image_id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey("users.id"))

    filename = db.Text()
    url = db.Column(db.Text())
    thumbnail = db.Column(db.Text())

    title = db.Column(db.Text(), default=None, nullable=True)
    description = db.Column(db.Text(), default=None, nullable=True)
    seo_hashtags = db.Column(db.Text(), default=None, nullable=True)
    brand = db.Column(db.Text(), nullable=True)
    category = db.Column(db.Text(), nullable=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def set_url(self, url):
        self.url = url

    def set_title(self, title):
        self.title = title

    def get_title(self):
        return self.title

    def set_desc(self, description):
        self.description = description

    def get_desc(self):
        return self.description

    def set_hashtags(self, seo_hashtags):
        self.seo_hashtags = seo_hashtags

    def get_hashtags(self):
        return self.seo_hashtags

    def set_thumbnail(self, thumb):
        self.thumbnail = thumb

    def set_user_id(self, id):
        self.user_id = id

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_all_images(cls, id):
        return cls.query.filter_by(user_id=id).all()


class JWTTokenBlocklist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jwt_token = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

    def __repr__(self):
        return f"Expired Token: {self.jwt_token}"

    def save(self):
        db.session.add(self)
        db.session.commit()
