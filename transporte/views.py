import os
import re
from datetime import datetime

import babel
from dateutil import parser
from flask import Markup, abort
from flask import current_app as app
from flask import (
    escape,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from jinja2 import evalcontextfilter
from werkzeug.utils import secure_filename

from email_validator import validate_email
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm

from . import db, login_manager
from .forms import (
    AddressForm,
    LoginForm,
    RoleForm,
    Roles,
    TransportFilterForm,
    TransportForm,
    VehicleTypes,
)
from .models import Address, File, Transport, User
from .zammad_integration import close_ticket, update_ticket


@app.route("/")
@login_required
def index():
    todo = (
        dict(description="Todays transports", progress=100,),
        dict(description="Overall transports", progress=100,),
    )

    today_start = datetime.combine(datetime.today().date(), datetime.min.time())
    today_end = datetime.combine(datetime.today().date(), datetime.max.time())
    transports_all = Transport.query.filter(
        Transport.state is not Transport.TransportState.cancelled
    )
    transports_today = transports_all.filter(Transport.start >= today_start).filter(
        Transport.start <= today_end
    )

    try:
        todo[0]["progress"] = (
            100
            / transports_today.count()
            * transports_today.filter(
                Transport.state is Transport.TransportState.done
            ).count()
        )
    except ZeroDivisionError:
        pass

    try:
        todo[1]["progress"] = (
            100
            / transports_all.count()
            * transports_all.filter(
                Transport.state is Transport.TransportState.done
            ).count()
        )
    except ZeroDivisionError:
        pass

    return render_template("layout.html", todo=todo)


@app.route("/login", methods=["GET", "POST"])
# @limiter.limit('10/hour')
def login():
    loginform = LoginForm()

    if loginform.validate_on_submit():
        email = loginform.login.data.lower()

        try:
            if not app.config["DEBUG"]:
                v = validate_email(email)
                email = v["email"]  # replace with normalized form

        except Exception as e:
            loginform.login.errors.append(str(e))

            return render_template("login.html", loginform=loginform)

        user = User.query.filter(User.login == email).first()

        if user is None:
            # create user
            user = User(login=email)
            db.session.add(user)
            db.session.commit()

        # create token
        user.mail_token()

        flash("Check your inbox!")

    return render_template("login.html", loginform=loginform)


@app.route("/login/token/<token>")
def login_with_token(token):
    user = User.verify_login_token(token)

    if user:
        login_user(user, remember=True)

        return redirect(url_for("index"))
    else:
        flash("Invalid or expired token!")
    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    logout_user()

    flash("You have been logged out.")

    return redirect(url_for("login"))


@app.route("/transports/add", defaults={"id": None}, methods=["GET", "POST"])
@app.route("/transports/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_transport(id=None):
    if id is not None:
        transport = Transport.query.get(id)

        if not (
            current_user.id == transport.user_id
            or current_user.role in ["helpdesk", "admin"]
        ):
            transport = None

    else:
        transport = Transport()

    if transport is not None:
        transportform = TransportForm(obj=transport)

        if transportform.validate_on_submit():
            transportform.populate_obj(transport)

            if id is None:
                transport.user_id = current_user.id
            db.session.add(transport)
            db.session.commit()

            #
            # if ticket is new, update object with zammad ticket id
            #
            if transport.ticket_id is None:
                transport.ticket_id = update_ticket(transport)
                db.session.add(transport)
                db.session.commit()
            else:
                update_ticket(transport)

            for file in request.files.getlist("file_upload"):
                if file.filename:
                    file_name = secure_filename(file.filename)
                    upload_dir = os.path.join(
                        app.config["UPLOAD_DIR"], str(transport.id)
                    )
                    file_path = os.path.join(upload_dir, file_name)

                    if not os.path.isdir(os.path.join(app.root_path, upload_dir)):
                        os.mkdir(os.path.join(app.root_path, upload_dir))

                    file.save(os.path.join(app.root_path, file_path))

                    f = File(transport_id=transport.id, name=file_name, path=file_path)
                    db.session.add(f)
                    db.session.commit()

            flash("Saved")

            if id is None:
                return redirect(url_for("edit_transport", id=transport.id))

    else:
        transportform = TransportForm()
        flash("Not authorized to edit this transport!")

    addresslist = Address.query

    if current_user.role not in ["admin", "helpdesk"]:
        addresslist = addresslist.filter(Address.public)

    addresslist = addresslist.all()

    return render_template(
        "transport_details_edit.html",
        transportform=transportform,
        transport=transport,
        addresslist=addresslist,
    )


@app.route("/transports/list")
@login_required
def list_transports():
    transportlist = Transport.query

    if current_user.role not in ["helpdesk", "admin"]:
        transportlist = transportlist.filter(Transport.user_id == current_user.id)

    filterform = TransportFilterForm(
        day=request.args.get("day"), hide_done=request.args.get("hide_done")
    )
    filterform.day.choices = [("None", "Filter by date")] + sorted(
        set(
            [
                (str(date[0].date()), str(date[0].date()))
                for date in transportlist.with_entities(Transport.start).all()
            ]
        )
    )

    if filterform.day.data != "None":
        date = parser.parse(filterform.day.data)
        filter_start = datetime.combine(date.date(), datetime.min.time())
        filter_end = datetime.combine(date.date(), datetime.max.time())
        transportlist = transportlist.filter(Transport.start >= filter_start).filter(
            Transport.start <= filter_end
        )
    if filterform.hide_done.data:
        transportlist = transportlist.filter(
            Transport.state != Transport.TransportState.done
        )
        transportlist = transportlist.filter(
            Transport.state != Transport.TransportState.cancelled
        )

    transportlist = transportlist.order_by(Transport.start)

    if transportlist.count() == 0:
        abort(404)

    return render_template(
        "transport_list.html", transportlist=transportlist, filterform=filterform
    )


@app.route("/transports/show/<int:id>")
@app.route("/transports/show/<int:id>/<string:format>")
@login_required
def show_transport(id=None, format=None):
    transport = Transport.query.get(id)

    if transport is None or not (
        transport.user_id == current_user.id
        or current_user.role in ["helpdesk", "admin"]
    ):
        transport = None
        flash("Transport is not available")
    else:
        if transport.done:
            flash("Transport is done", "success")
        elif transport.cancelled:
            flash("Transport was cancelled!", "danger")

    if format == "sticker":
        template = "transport_sticker.html"
    else:
        template = "transport_details.html"
    return render_template(template, transport=transport)


@app.route("/transports/mark/<mark>/<int:id>", methods=["GET", "POST"])
@login_required
def mark_transport(mark, id=None):
    transport = Transport.query.get(id)

    if transport is None or not (
        transport.user_id == current_user.id
        or current_user.role in ["helpdesk", "admin"]
    ):
        transport = None
        flash("Transport not available")
    elif transport.state == Transport.TransportState.done:
        flash("Transport already marked as done!")
        transport = None
    elif transport.state == Transport.TransportState.cancelled:
        flash("Transport cancelled!")
        transport = None

    form = FlaskForm()

    if form.validate_on_submit():
        if mark == "done" and current_user.role in ["helpdesk", "admin"]:
            transport.state = Transport.TransportState.done
        elif mark == "cancelled":
            transport.state = Transport.TransportState.cancelled

        #
        # close ticket
        #
        if transport.ticket_id:
            close_ticket(transport, mark)

        db.session.add(transport)
        db.session.commit()

        return redirect(url_for("list_transports"))

    return render_template(
        "transport_mark.html", mark=mark, transport=transport, form=form
    )


@app.route("/addresses/list")
@login_required
def list_addresses():
    if not (current_user.role in ["helpdesk", "admin"]):
        abort(404)

    addresses = Address.query.all()

    return render_template("address_list.html", addresslist=addresses)


@app.route("/addresses/add", defaults={"id": None}, methods=["GET", "POST"])
@app.route("/addresses/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_address(id=None):
    if not (current_user.role in ["helpdesk", "admin"]):
        abort(404)

    if id is not None:
        address = Address.query.get(id)

        if not (current_user.id == address.user_id or current_user.role in ["admin"]):
            address = None
    else:
        address = Address()

    if address is not None:
        addressform = AddressForm(obj=address)

        if addressform.validate_on_submit():
            addressform.populate_obj(address)

            if id is None:
                address.user_id = current_user.id
            db.session.add(address)
            db.session.commit()

            flash("Saved!")

            if id is None:
                return redirect(url_for("edit_address", id=address.id))

    else:
        addressform = AddressForm()
        flash("Not authorized to edit this address!")

    return render_template(
        "address_edit.html", addressform=addressform, address=address
    )


@app.route("/addresses/del/<int:id>", methods=["GET", "POST"])
@login_required
def delete_address(id):
    address = Address.query.get(id)

    if (
        address is None
        or current_user.id is not address.user_id
        or current_user.role not in ["admin"]
    ):
        abort(404)

    form = FlaskForm()

    if form.validate_on_submit():
        db.session.delete(address)
        db.session.commit()

        return redirect(url_for("list_addresses"))

    return render_template("address_delete.html", form=form, address=address)


@app.route("/users/list")
@login_required
def list_users():
    if not (current_user.role in ["admin"]):
        abort(404)

    users = User.query.all()

    return render_template("user_list.html", userlist=users)


@app.route("/users/show/<int:id>", methods=["GET", "POST"])
@login_required
def edit_user(id=None):
    if not (current_user.role in ["admin"]):
        abort(404)

    user = User.query.get(id)
    roleform = RoleForm(obj=user)

    if user is None:
        flash("User not available")
    elif roleform.validate_on_submit():
        roleform.populate_obj(user)

        db.session.add(user)
        db.session.commit()

        flash("Saved")

    return render_template("user_details.html", user=user, roleform=roleform)


@app.route("/me", methods=["GET"])
@login_required
def me():
    token = current_user.create_token()
    return render_template("me.html", token=token)


@app.route("/uploads/<int:transport_id>/<path:filename>")
def uploaded_file(transport_id, filename):
    transport = Transport.query.get(transport_id)

    if transport is None or not (
        transport.user_id == current_user.id
        or current_user.role in ["helpdesk", "admin"]
    ):
        abort(404)

    return send_from_directory(
        os.path.join(app.config["UPLOAD_DIR"], str(transport_id)), filename
    )


def format_datetime(value):
    format = "EE, dd.MM.y"
    return babel.dates.format_datetime(value, format)


_paragraph_re = re.compile(r"(?:\r\n|\r|\n)")


@evalcontextfilter
def oneline(eval_ctx, value):
    return u";".join(_paragraph_re.split(escape(value)))


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u"<br />\n".join(_paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


app.jinja_env.filters["datetime"] = format_datetime
app.jinja_env.filters["oneline"] = oneline
app.jinja_env.filters["nl2br"] = nl2br


@app.context_processor
def inject_global_template_vars():
    return dict(app_name=app.config["APP_NAME"], vehicletypes=VehicleTypes, roles=Roles)


@app.context_processor
def inject_today():
    return dict(today=datetime.today().date())


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
