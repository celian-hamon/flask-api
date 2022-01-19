import hashlib
import os
from sqlite3 import Cursor
from flask import Flask, jsonify, request
from tests import test_possede, test_sonde, test_user, test_releve
import mysql.connector


# TODO gestion authentification (optionnel)
# TODO releve with sonde id
# ? Sonde peut avoir plusieurs users ou 0 users
# ? Releve a besoin du user

app = Flask(__name__)
conn = mysql.connector.connect(
    host="localhost", user="root", password="root", database="cube")


testLib = {
    "releve": test_releve.main,
    "sonde": test_sonde.main,
    "user": test_user.main,
    "possede": test_possede.main,
    "full": [test_releve.main, test_sonde.main, test_user.main, test_possede.main],
}


# sonde part
@app.route("/sonde/<uid>", methods=['GET'], endpoint='getSonde')
def getSonde(uid):

    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    password = header["password"]
    sonde_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM `sonde` WHERE `id` = %s", (sonde_id,))
        sonde = cursor.fetchone()
        if sonde is not None:
            return jsonify(
                id=sonde[0],
                active=sonde[1],
                latitude=sonde[2],
                longitude=sonde[3],
            ), 200
        else:
            return jsonify({"error": "sonde not found"}), 404
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


@app.route("/sonde/solo", methods=['GET'], endpoint='getSondeSolo')
def getSondeSolo():
    header = request.headers
    profile_id = header["profile"]
    admin = isAdmin(profile_id)

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    if admin:
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT `id` FROM `sonde`")
        sonde = cursor.fetchall()
        soloSonde = []
        for i in sonde:
            cursor.execute(
                "SELECT `id_user` FROM `possede` WHERE `id_sonde` = %s", (i[0],))
            possede = cursor.fetchone()
            if possede is None:
                soloSonde.append(i[0])
        return jsonify(soloSonde), 200
    elif not admin:
        return jsonify({"error": "forbidden"}), 403


@app.route("/sonde", methods=['POST'], endpoint='createSonde')
def createSonde():
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]

    # retrieve the data from the body
    body = request.get_json()
    latitude = body["latitude"]
    longitude = body["longitude"]

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO `sonde` (active,latitude,longitude) VALUES (1,%s,%s)", (latitude, longitude,))
    conn.commit()
    cursor.execute("SELECT LAST_INSERT_ID()")
    sonde_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO `possede` (id_sonde,id_user) VALUES (%s,%s)", (sonde_id, profile_id,))
    conn.commit()
    return jsonify(
        id=sonde_id,
        active=1,
        latitude=latitude,
        longitude=longitude,
    ), 201


@app.route("/sonde/<uid>", methods=['PUT'], endpoint='updateSonde')
def updateSonde(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":

        cursor = conn.cursor()

        body = request.get_json()
        latitude = body["latitude"]
        longitude = body["longitude"]

        cursor.execute("UPDATE `sonde` SET `latitude` = %s, `longitude` = %s WHERE `id` = %s",
                       (latitude, longitude, sonde_id,))
        conn.commit()
        return jsonify(
            id=sonde_id,
            active=1,
            latitude=latitude,
            longitude=longitude,
        ), 200
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


@app.route("/sonde/<uid>", methods=['DELETE'], endpoint='deleteSonde')
def deleteSonde(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM `sonde` WHERE `id` = %s", (sonde_id,))
        sonde = cursor.fetchone()
        if sonde is not None:
            cursor.execute(
                "DELETE FROM `possede` WHERE `id_sonde` = %s", (sonde_id,))
            conn.commit()
            cursor.execute("DELETE FROM `sonde` WHERE `id` = %s", (sonde_id,))
            conn.commit()
            return jsonify({"success": "sonde deleted"}), 200
        else:
            return jsonify({"error": "sonde not found"}), 404
    elif status == "False":
        return jsonify({"error": "forbidden"}), 403


@app.route("/sonde/<uid>/desactivate", methods=['PUT'], endpoint='desactivateSonde')
def desactivateSonde(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":
        cursor = conn.cursor()
        cursor.execute(
            "SELECT `active` FROM `sonde` WHERE `id` = %s", (sonde_id,))
        active = cursor.fetchone()[0]
        if active == 1:
            cursor.execute(
                "UPDATE `sonde` SET `active` = %s WHERE `id` = %s", (0, sonde_id,))
            conn.commit()
            return jsonify({"success": "sonde desactivated"}), 200
        elif active == 0:
            # TODO : change to logic error code
            return jsonify({"error": "sonde already desactivated"}), 400
        return jsonify({"error": "sonde not found"}), 404
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


@app.route("/sonde/<uid>/activate", methods=['PUT'], endpoint='activateSonde')
def activateSonde(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":
        cursor = conn.cursor()
        cursor.execute(
            "SELECT `active` FROM `sonde` WHERE `id` = %s", (sonde_id,))
        active = cursor.fetchone()[0]
        if active == 0:
            cursor.execute(
                "UPDATE `sonde` SET `active` = %s WHERE `id` = %s", (1, sonde_id,))
            conn.commit()
            return jsonify({"success": "sonde activated"}), 200
        elif active == 1:
            return jsonify({"error": "sonde already active"}), 400
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


@app.route("/sonde/<sonde_uid>/user/<user_uid>", methods=['PUT'], endpoint='addUserToSonde')
def addUserToSonde(sonde_uid, user_uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['sonde_uid']
    user_id = request.view_args["user_uid"]

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":
        cursor = conn.cursor()

        cursor.execute(
            "SELECT `id_sonde` FROM `possede` WHERE `id_sonde` = %s AND `id_user` = %s", (sonde_id, user_id,))
        sonde = cursor.fetchone()

        if sonde is None:
            cursor.execute(
                "INSERT INTO `possede` (id_sonde,id_user) VALUES (%s,%s)", (sonde_id, user_id,))
            conn.commit()
            return jsonify({"success": "user added to sonde"}), 200
        else:
            # TODO : change to logic error code
            return jsonify({"error": "user already in sonde"}), 400
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


@app.route("/sonde/<sonde_uid>/user/<user_uid>", methods=['DELETE'], endpoint='removeUserFromSonde')
def removeUserFromSonde(sonde_uid, user_uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = request.view_args['sonde_uid']
    user_id = request.view_args["user_uid"]

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    status = ownSonde(sonde_id, profile_id)

    if status == "True":
        cursor = conn.cursor()
        cursor.execute(
            "SELECT `id_sonde` FROM `possede` WHERE `id_sonde` = %s AND `id_user` = %s", (sonde_id, user_id,))
        sonde = cursor.fetchone()

        if sonde is not None:

            cursor.execute(
                "DELETE FROM `possede` WHERE `id_sonde` = %s AND `id_user` = %s", (sonde_id, user_id,))
            conn.commit()

            return jsonify({"success": "user removed from sonde"}), 200
        else:
            # TODO : change to logic error code
            return jsonify({"error": "user not in sonde"}), 400
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


# user part
@app.route("/user/<uid>", methods=['GET'], endpoint='getUser')
def getUser(uid):
    header = request.headers
    user_id = request.view_args['uid']
    profile_id = header["profile"]
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `user` WHERE `id` = %s", (user_id,))
    user = cursor.fetchone()

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    if user is not None and (user[0] == user_id or str(user[2]) == "1"):
        return jsonify(
            id=user[0],
            name=user[1],
            admin=user[2],
        ), 200
    else:
        return jsonify({"error": "user not found"}), 404


@app.route("/user/<uid>/sonde", methods=['GET'], endpoint='getUserSonde')
def getUserSonde(uid):
    header = request.headers
    profile_id = header["profile"]

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = request.view_args['uid']
    if user_id == profile_id or isAdmin(profile_id):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT `id_sonde` FROM `possede` WHERE `id_user` = %s", (user_id,))
        sonde = cursor.fetchall()
        if sonde is not None:
            sonde_list = []
            for sonde_id in sonde:
                cursor.execute(
                    "SELECT * FROM `sonde` WHERE `id` = %s", (sonde_id[0],))
                sonde_list.append(cursor.fetchone())
            return jsonify(sonde_list), 200
        else:
            return jsonify({"error": "user has no sonde"}), 404
    else:
        return jsonify({"error": "forbidden"}), 403


@ app.route("/user/<uid>", methods=['PUT'], endpoint='updateUser')
def updateUser(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    user_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    # check if the user exist
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `user` WHERE `id` = %s", (user_id,))

    if cursor.fetchone() is not None:
        # si le user existe, on vérifie que le user a le droit d'etre modifié
        # si il est admin  il peut modifier tout le monde et tout les champs
        if isAdmin(profile_id):

            body = request.get_json()
            name = body["name"]
            admin = body["admin"]

            cursor.execute(
                "UPDATE `user` SET `name` = %s, `admin` = %s WHERE `id` = %s", (name, admin, user_id,))
            conn.commit()
            return jsonify(
                id=user_id,
                name=name,
                admin=admin,
            ), 200

        # si il est pas admin il peut modifier uniquement son nom
        elif user_id == profile_id:

            body = request.get_json()
            name = body["name"]

            cursor.execute(
                "UPDATE `user` SET `name` = %s WHERE `id` = %s", (name, user_id,))
            conn.commit()
            return jsonify(
                id=user_id,
                name=name,
            ), 200
        # sinon erreur 403 interdit
        else:
            return jsonify({"error": "forbidden"}), 403
    else:
        return jsonify({"error": "user not found"}), 404


@ app.route("/user", methods=['POST'], endpoint='createUser')
def createUser():
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    cursor = conn.cursor()

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    body = request.get_json()
    name = body["name"]
    admin = body["admin"]

    # check if the name is already used
    cursor.execute("SELECT * FROM `user` WHERE `name` = %s", (name,))
    if cursor.fetchone() is not None:
        return jsonify({"error": "username is already taken"}), 400

    if isAdmin(profile_id):

        encrypted_salt, encrypted_pd = encryptPassword(body["password"])

        cursor.execute(
            "INSERT INTO `user` (`name`,`admin`,`password`,`salt`) VALUES (%s,%s,%s,%s)", (name, admin, encrypted_pd, encrypted_salt,))
        conn.commit()
        return jsonify(
            id=cursor.lastrowid,
            name=name,
            admin=admin,
        ), 201
    else:
        return jsonify({"error": "forbidden"}), 403


@ app.route("/user/<uid>", methods=['DELETE'], endpoint='deleteUser')
def deleteUser(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    user_id = request.view_args['uid']

    # authentification
    password = header["password"]
    if checkPassword(profile_id, password_try=password) is False:
        return jsonify({"error": "Unauthorized"}), 401

    if isAdmin(profile_id) or user_id == profile_id:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM `user` WHERE `id` = %s", (user_id,))
        user = cursor.fetchone()
        if user is not None:
            cursor.execute(
                "DELETE FROM `possede` WHERE `id_user` = %s", (user_id,))
            conn.commit()
            cursor.execute("DELETE FROM `user` WHERE `id` = %s", (user_id,))
            conn.commit()
            return jsonify({"success": "user deleted"}), 200
        else:
            return jsonify({"error": "user not found"}), 404
    else:
        return jsonify({"error": "forbidden"}), 403

# relevé part


# GET RELEVÉ
@ app.route("/releve/<uid>", methods=['GET'], endpoint='getReleve')
def getReleve(uid):
    releve_id = request.view_args['uid']
    profile_id = request.headers["profile"]

    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM `releve` WHERE `id` = %s", (releve_id,))
    releve = cursor.fetchone()

    status = ownSonde(profile_id, releve[4])

    if releve is not None:
        if status == "True":
            return jsonify(
                id=releve[0],
                date=releve[1],
                temperature=releve[2],
                humidite=releve[3],
                id_sonde=releve[4],
            ), 200
        elif status == "False":
            return jsonify({"error": "you are not the owner of this sonde"}), 403
        elif status == "user404":
            return jsonify({"error": "user not found"}), 404
        elif status == "sonde404":
            return jsonify({"error": "sonde not found"}), 404
    else:
        return jsonify({"error": "releve not found"}), 404


# CREATE RELEVÉ
@ app.route("/releve", methods=['POST'], endpoint='createReleve')
def createReleve():
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    sonde_id = header["sonde"]
    cursor = conn.cursor()

    body = request.get_json()
    temp = body["temperature"]
    hum = body["humidite"]
    status = ownSonde(profile_id, sonde_id)

    if status == "True":
        cursor.execute(
            "INSERT INTO `releve` (`temperature`,`humidite`,`id_sonde`) VALUES (%s,%s,%s)", (temp, hum, sonde_id))
        conn.commit()

        return jsonify(
            id=cursor.lastrowid,
            temp=temp,
            hum=hum,
            id_sonde=sonde_id,
        ), 201
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


# DELETE RELEVÉ
@ app.route("/releve/<uid>", methods=['DELETE'], endpoint='deleteReleve')
def deleteReleve(uid):
    # retrieve the data from the request
    header = request.headers
    profile_id = header["profile"]
    releve_id = request.view_args['uid']

    cursor = conn.cursor()
    cursor.execute(
        "SELECT `id_sonde` FROM `releve` WHERE `id` = %s", (releve_id,))
    sonde_id = cursor.fetchone()[0]

    status = ownSonde(profile_id, sonde_id)
    if status == "True":
        cursor.execute("SELECT * FROM `releve` WHERE `id` = %s", (releve_id,))
        releve = cursor.fetchone()
        if releve is not None:
            cursor.execute(
                "DELETE FROM `releve` WHERE `id` = %s", (releve_id,))
            conn.commit()
            return jsonify({"success": "releve deleted"}), 200
        else:
            return jsonify({"error": "releve not found"}), 404
    elif status == "False":
        return jsonify({"error": "you are not the owner of this sonde"}), 403
    elif status == "user404":
        return jsonify({"error": "user not found"}), 404
    elif status == "sonde404":
        return jsonify({"error": "sonde not found"}), 404


# tests part
@ app.route("/test", methods=['POST'], endpoint='runTest')
def runTest():
    # retrieve the data from the request
    header = request.headers
    profile = header["profile"]

    body = request.get_json()
    test = body["test"]

    if profile == "test" and body["test"] is not None:
        if test == "full":
            try:
                for i in range(len(testLib["full"])):
                    testLib["full"][i]()
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            try:
                testLib[test]()
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({"success": "test passed"}), 200
    else:
        return jsonify({"error": "forbidden"}), 403


def ownSonde(sonde, profile):

    cursor = conn.cursor()

    if isAdmin(profile):
        return "True"
    else:
        # check if both user and sonde exists
        cursor.execute("SELECT * FROM `user` WHERE `id` = %s", (profile,))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM `sonde` WHERE `id` = %s", (sonde,))
        sonde = cursor.fetchone()
        if user is not None and sonde is not None:
            # check if the user is the owner of the sonde
            cursor.execute(
                "SELECT * FROM `possede` WHERE `id_user` = %s AND `id_sonde` = %s", (profile, sonde[0]))
            possede = cursor.fetchone()
            if possede is not None:
                return "True"
            else:
                return "False"
        else:
            if user is None:
                return "user404"
            else:
                return "sonde404"


def encryptPassword(password):
    # Example generation
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt, key


# check if the password is correct
def checkPassword(user_id, password_try):
    # check if the user exit and retreive the salt and the key
    cursor = conn.cursor()
    cursor.execute(
        "SELECT `password`,`salt` FROM `user` WHERE `id` = %s", (user_id,))
    user = cursor.fetchone()

    # if the user exist
    if user is not None:
        password = bytes(user[0])
        salt = bytes(user[1])

        # encode password_try with the same salt as the password stored in database
        key2 = hashlib.pbkdf2_hmac(
            'sha256', password_try.encode('utf-8'), salt, 100000)

        # compare the two key
        if key2 == password:
            return "True"
        else:
            return "False"


def isAdmin(profile):
    cursor = conn.cursor()

    query = "SELECT `admin` FROM `user` WHERE `id` = %s"
    cursor.execute(query, (profile,))
    row = cursor.fetchone()
    if row is not None:
        if row[0] == 1:
            return True
        else:
            return False
