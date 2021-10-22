from flask import Flask,render_template,request,flash, session
import sqlite3,bcrypt,os
from werkzeug.utils import redirect
app = Flask(__name__) 
app.secret_key = os.urandom(24)

### Rutas
@app.route('/')
@app.route('/Home')
def index():
    return render_template('index.html',titulo='Gold Star Chili',bodyid='bodyIndex')

@app.route('/Login',methods=["GET","POST"])
def login():
    if es_usuario():
        flash("exito")
        return redirect('/Usuario/')
    else:
        if request.method == 'POST':
            usuario = request.form.get("usuario_login")
            password = request.form.get("password_login")

            query = "select NIT,nombre,usuario,contrasena,tipousuarios_id,p.id from usuarios as u left join pedido as p on u.NIT = p.usuarios_nit where usuario = ? and p.confirmado = false"
            parametros = [(usuario)]
            usuarioResult = consultarBD(query,parametros)
            if '_flashes' in session:
                session['_flashes'].clear()
            if usuarioResult:
                password = password.encode()
                if bcrypt.checkpw(password,usuarioResult[0][3]):
                    login_user(usuarioResult)
                    flash("exito")
                    return redirect('/Usuario/')
                else:
                    flash("fallido")
            else:
                flash("fallido")
    return render_template('login.html',titulo='Iniciar sesion')

@app.route("/Logout")
def logout():
    if es_usuario():
        logout_user()
        return redirect('/Login')
    return redirect('/')

@app.route('/Registro',methods=["GET","POST"])
def registrar():
    if request.method == 'POST':
        Nit = request.form.get("No_documento")
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        telefono = request.form.get("telefono")
        email = request.form.get("email")
        f_nacimiento = request.form.get("fecha_nacimiento")
        direccion = request.form.get("direccion")
        usuario = request.form.get("usuario")
        password = request.form.get("password")
        #Encriptar contraseña
        password = password.encode()
        key = bcrypt.gensalt()
        passwordEncriptada = bcrypt.hashpw(password, key)

        statement = "insert into usuarios(NIT,nombre,apellido,telefono,correoelectronico,fechanacimiento,direccion,usuario,contrasena,tipousuarios_id) values (?,?,?,?,?,?,?,?,?,?)"
        parametros = (Nit,nombre,apellido,telefono,email,f_nacimiento,direccion,usuario,passwordEncriptada,1)
        
        row_id = modificarBD(statement,parametros)
        user = consultarBD("SELECT usuario FROM usuarios WHERE NIT = ?;",[(row_id)])
        if '_flashes' in session:
            session['_flashes'].clear()
        flash("registroExito|"+str(user))
        return redirect('/Login')

    return render_template('registro.html',titulo='Registro usuario')

@app.route('/Menu',methods=["GET","POST"])
def mostrarMenu(platos=None):
    try:
        sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
        cursor = sqliteConnection.cursor()

        query = "SELECT id, nombre, precio, descripcion, imagen FROM platos;"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("The SQLite connection is closed")

    if request.method == 'POST' and 'nit' in session:
        id_plato = request.form.get('id_plato')
        precio = request.form.get('precio')
        usuario_nit= session["nit"]
        try:
            sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
            cursor = sqliteConnection.cursor()

            pedidoActivo = "Select id from pedido where usuarios_nit = ? and Confirmado = false;"
            cursor.execute(pedidoActivo,[(usuario_nit)])
            id_pedido = cursor.fetchone()
            if(id_pedido == None):
                insertPedido = "INSERT INTO pedido (total,usuarios_nit) VALUES (?,?);"
                cursor.execute(insertPedido,(0,usuario_nit))
                sqliteConnection.commit()
                pedido = cursor.lastrowid
            else:
                pedido = id_pedido[0]
            insertDetalle = "INSERT INTO detalles_plato(platos_id, pedido_id, cantidad, subtotal) VALUES(?,?,?,?);"
            cursor.execute(insertDetalle,(id_plato,pedido,1,precio))
            sqliteConnection.commit()
            cursor.close()
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")
    else:
        if '_flashes' in session:
            session['_flashes'].clear()
        flash("login_failed")
    return render_template('menu.html',titulo='Menu de platillos',platos=result)

@app.route('/Menu/detalle_plato/<int:id_plato>',methods=["GET"])
def detallesPlatoID(id_plato=None):
    try:
        sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
        cursor = sqliteConnection.cursor()
        preparedstatement = "SELECT id, nombre, precio, descripcion, imagen FROM platos WHERE id = ?;"
        
        cursor.execute(preparedstatement,[(id_plato)])
        result = cursor.fetchone()
        cursor.close()
    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("The SQLite connection is closed")
    return render_template('detalle.html',titulo='Detalles del plato',plato=result)

@app.route('/Lista_deseos')
def listarDeseos(platos=None):
    platillos=[
        {"id_plato":1 , "nombre":"Hamburguesa de Carne" , "precio":20000 , "img":"hamburguesa.jpg"},
        {"id_plato":2 , "nombre":"Pasta alfredo" , "precio":30000 , "img":"pasta.png"},
        {"id_plato":3 , "nombre":"Lasaña de carne" , "precio":50000 , "img":"lasana.jpg"},
        {"id_plato":4 , "nombre":"Carne Asada" , "precio":28000 , "img":"carne.jpg"}
    ]
    return render_template('listaDeseos.html',titulo='Lista de Deseos',platos=platillos)

@app.route('/Pedidos/')
def pedidos():
    detalles=[]
    if es_usuario():
        usuario = usuario_actual()
        statement = "SELECT p.id, nombre, precio, imagen,cantidad,subtotal FROM platos as p inner join detalles_plato dp ON p.id = dp.platos_id where dp.pedido_id = ?;"
        parametros = [(usuario["pedido"])]
        detalles = consultarBD(statement,parametros)
    else:
        if '_flashes' in session:
            session['_flashes'].clear()
        flash("login_failed")
    return render_template('pedidos.html',titulo='Carrito de compras',platos = detalles)

@app.route('/Usuario/',methods=["GET","POST"])
def perfilUsuario():
    if es_usuario():
        usuarioActual = usuario_actual()
        if request.method == "POST":
            statement="UPDATE usuarios SET nombre = ?,apellido = ?,telefono = ?,correoelectronico = ?,fechanacimiento = ?,direccion = ? WHERE NIT = ?"
            nombre = request.form.get("nombre")
            apellido = request.form.get("apellido")
            telefono = request.form.get("telefono")
            email = request.form.get("email")
            f_nacimiento = request.form.get("fecha_nacimiento")
            direccion = request.form.get("direccion")
            parametros=(nombre,apellido,telefono,email,f_nacimiento,direccion,usuarioActual['nit'])
            row_id = modificarBD(statement,parametros)
            if '_flashes' in session:
                session['_flashes'].clear()
            flash("usuarioActualizado")
        statement="SELECT nombre,apellido,correoelectronico, telefono, fechanacimiento, direccion FROM usuarios where NIT = ?"
        parametros=[(usuarioActual["nit"])]
        datos = consultarBD(statement,parametros)
        return render_template('usuario_perfil.html',titulo='Perfil del usuario',usuario=usuario_actual(),datos=datos[0])
    if '_flashes' in session:
        session['_flashes'].clear()
    flash("login_failed")
    return redirect('/Login')

@app.route('/Usuario/Cuenta/',methods=["GET","POST"])
def configuracionUsuario():
    if es_usuario():
        usuarioActual = usuario_actual()
        if request.method == "POST":
            passwordActual = request.form.get("passwordActual")
            statement="SELECT contrasena FROM usuarios WHERE NIT = ?;"
            parametros=[(usuarioActual["nit"])]

            passwordResult = consultarBD(statement,parametros)

            passwordActual = passwordActual.encode()
            if '_flashes' in session:
                session['_flashes'].clear()
            if bcrypt.checkpw(passwordActual,passwordResult[0][0]):
                nuevoPassword = request.form.get("nuevoPassword")
                nuevoPassword = nuevoPassword.encode()
                key = bcrypt.gensalt()
                passwordEncriptada = bcrypt.hashpw(nuevoPassword, key)
                statement="UPDATE usuarios SET contrasena = ? WHERE NIT = ?;"
                parametros=(passwordEncriptada,usuarioActual["nit"])
                row_id = modificarBD(statement,parametros)
                flash("cambioPass")
            else:
                flash("fallido")
        return render_template('usuario_configuracion.html',titulo='Configuracion de cuenta',usuario=usuario_actual())
    
    if '_flashes' in session:
        session['_flashes'].clear()
    flash("login_failed")
    return redirect('/Login')

@app.route('/Usuario/Pedidos/')
def pedidosUsuarios():
    return render_template('usuario_pedidos.html',titulo='Pedidos del usuario')

@app.route('/Usuario/Administrador')
def ingresoAdministrador():
    return render_template('administrador.html',titulo='Administrador Dashboard')

@app.route('/Usuario/Comentarios')
def gestionComentarios():
    return render_template('gestionar_comentarios.html',titulo='Gestionar comentarios')

@app.route('/Usuario/Administrador/GestionarUsuarios')
def gestionUsuarios():
    return render_template('gestionar_usuarios.html',titulo='Gestionar usuarios')

### Funciones
def consultarBD(query,params):
    if(query != ''):
        try:
            sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
            cursor = sqliteConnection.cursor()

            if params:
                cursor.execute(query,params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")
            return result

def modificarBD(statement,params):
    if(statement != ''):
        try:
            sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
            cursor = sqliteConnection.cursor()

            if params:
                cursor.execute(statement,params)
            else:
                cursor.execute(statement)
            sqliteConnection.commit()
            row_id = cursor.lastrowid
            cursor.close()
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")
            return row_id

def login_user(usuario):
    session["nit"] = usuario[0][0]
    session["nombre"] = usuario[0][1]
    session["usuario"] = usuario[0][2]
    session["tipo"] = usuario[0][4]
    session["pedido"] = usuario[0][5]

def logout_user():
    session.pop("nit", None)
    session.pop("nombre", None)
    session.pop("usuario", None)
    session.pop("tipo", None)
    session.pop("pedido", None)

def usuario_actual():
    usuario = { "nit" : session["nit"] ,
                "nombre" : session["nombre"],
                "usuario" : session["usuario"],
                "tipo" : session["tipo"],
                "pedido" : session["pedido"]}
    return usuario

def es_usuario():
    if 'nit' in session:
        return True
    else:
        return False

def es_admin():
    if 'tipo' in session:
        if session['tipo'] == 2:
            return True
    return False

def es_superadmin():
    if 'tipo' in session:
        if session['tipo'] == 3:
            return True
    return False

if __name__=="__main__":
    app.run(port=5000,debug=True)