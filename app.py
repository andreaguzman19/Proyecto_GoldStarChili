from flask import Flask,render_template,request,flash, session
import sqlite3,bcrypt,os
from werkzeug.utils import redirect
app = Flask(__name__) 
app.secret_key = os.urandom(24)

### Rutas
@app.route('/')
@app.route('/Home')
def index():
    carrito = None
    if es_usuario():
        if session['pedido']!=None:
            carrito = consultarBD("SELECT p.id, nombre, precio, imagen,cantidad,subtotal FROM platos as p inner join detalles_plato dp ON p.id = dp.platos_id where dp.pedido_id = ?;",[(session['pedido'])])
    return render_template('index.html',titulo='Gold Star Chili',bodyid='bodyIndex',carrito=carrito)

@app.route('/Login',methods=["GET","POST"])
def login():
    if es_usuario():
        limpiarMensajes()
        flash("exito")
        return redirect('/Usuario/')
    else:
        if request.method == 'POST':
            usuario = request.form.get("usuario_login")
            password = request.form.get("password_login")

            query = "SELECT NIT,nombre,usuario,contrasena,tipousuarios_id,p.id,p.confirmado FROM usuarios as u LEFT JOIN pedido as p on u.NIT = p.usuarios_nit WHERE usuario = ?;"
            parametros = [(usuario)]
            usuarioPedido = consultarBD(query,parametros)
            limpiarMensajes()
            if usuarioPedido:
                password = password.encode()
                if bcrypt.checkpw(password,usuarioPedido[0][3]):
                    pedidoEnProgreso = False
                    for item in usuarioPedido:
                        if item[6] == False:
                            pedidoEnProgreso = True
                            login_user(item,item[5])
                            break
                    if not pedidoEnProgreso:
                        login_user(usuarioPedido[0],None)
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

        statement = "INSERT INTO usuarios(NIT,nombre,apellido,telefono,correoelectronico,fechanacimiento,direccion,usuario,contrasena,tipousuarios_id) VALUES (?,?,?,?,?,?,?,?,?,?)"
        parametros = (Nit,nombre,apellido,telefono,email,f_nacimiento,direccion,usuario,passwordEncriptada,1)
        
        row_id = modificarBD(statement,parametros)
        user = consultarBD("SELECT usuario FROM usuarios WHERE NIT = ?;",[(row_id)])
        limpiarMensajes()
        flash("registroExito|"+str(user[0][0]))
        return redirect('/Login')

    return render_template('registro.html',titulo='Registro usuario')

@app.route('/Menu',methods=["GET","POST"])
def mostrarMenu():
    statement = "SELECT id, nombre, precio, descripcion, imagen FROM platos;"
    result = consultarBD(statement,None)
    deseos = None

    if es_usuario():
        if request.method == 'POST':
            if not request.form.get('precio'):
                id_plato = request.form.get('id_plato_deseos')
                deseoActivo = request.form.get('deseoActivo')
                limpiarMensajes()
                if deseoActivo == "false":
                    statement = "INSERT INTO deseos (platos_id,usuarios_nit) VALUES ( ? , ? );"
                    parametros = (id_plato,session["nit"])
                    row_id = modificarBD(statement,parametros)
                    flash("deseo_OK")
                else:
                    statement = "DELETE FROM deseos WHERE platos_id = ? AND usuarios_nit = ?;"
                    parametros = (id_plato,session["nit"])
                    row_id = modificarBD(statement,parametros)
                    flash("borrar_deseo")      

            else:
                id_plato = request.form.get('id_plato_carrito')
                precio = request.form.get('precio')
                if session["pedido"] == None:
                    statement = "INSERT INTO pedido (total,usuarios_nit) VALUES ( ? , ? );"
                    parametros = (0,session["nit"])
                    pedido_id = modificarBD(statement,parametros)
                    session["pedido"] = pedido_id
                statement = "INSERT INTO detalles_plato(platos_id, pedido_id, cantidad, subtotal) VALUES(?,?,?,?);"
                parametros = (id_plato,session["pedido"],1,precio)
                respuesta = modificarBD(statement,parametros)
                limpiarMensajes()
                if isinstance(respuesta,str):
                    if respuesta == "plato_registrado":
                        flash(respuesta)
                else:
                    flash("OK")
        statement = "SELECT platos_id FROM deseos WHERE usuarios_nit = ?;"
        deseos = consultarBD(statement,[(session["nit"])])
    else:
        if request.method == 'POST':
            limpiarMensajes()
            flash("login_failed")
            return redirect('/Login')
    return render_template('menu.html',titulo='Menu de platillos',platos=result,deseos=deseos)

@app.route('/Menu/detalle_plato/<int:id_plato>',methods=["GET"])
def detallesPlatoID(id_plato=None):
    statement = "SELECT id, nombre, precio, descripcion, imagen FROM platos WHERE id = ?;"
    result = consultarBD(statement,[(id_plato)])
    if result:
        plato = result[0]
    else:
        plato = None
    return render_template('detalle.html',titulo='Detalles del plato',plato=plato)

@app.route('/Lista_deseos/',methods=["GET","POST"])
def listarDeseos():
    platillos=[]
    if es_usuario():
        if request.method == "POST":
            id_plato = request.form.get('id_plato')
            statement = "DELETE FROM deseos WHERE platos_id = ? AND usuarios_nit = ?;"
            parametros = (id_plato,session["nit"])
            row_id = modificarBD(statement,parametros)
        statement = "SELECT p.id,nombre,precio,imagen FROM deseos as d INNER JOIN platos p ON d.platos_id = p.id WHERE usuarios_nit = ?;"
        platillos = consultarBD(statement,[(session["nit"])])
    else:
        limpiarMensajes()
        flash('login_failed')
        redirect("/Login")
    return render_template('listaDeseos.html',titulo='Lista de Deseos',platos=platillos)

@app.route('/Pedidos/',methods=["GET","POST"])
def pedidos():
    detalles=[]
    if es_usuario():
        if request.method == "POST":
            solicitud = request.form.get('request')
            if solicitud == 'borraDetalle':
                id_plato_borrar = request.form.get('id_plato_borrar')
                statement = "DELETE FROM detalles_plato WHERE platos_id = ? AND pedido_id = ?;"
                parametros = (id_plato_borrar,session["pedido"])
                row_id = modificarBD(statement,parametros)
            else:
                if solicitud == 'confirmaPedido':
                    total = request.form.get('total_confirmado')
                    statement = 'UPDATE pedido SET total = ?, Confirmado = ? WHERE id = ?';
                    parametros = (total,True,session["pedido"])
                    row_id = modificarBD(statement,parametros)
                    session["pedido"] = None
                    limpiarMensajes()
                    flash("pedidoConfirmado")
                    return redirect('/Usuario/Pedidos/')
        if session["pedido"] != None:
            statement = "SELECT p.id, nombre, precio, imagen,cantidad,subtotal FROM platos as p inner join detalles_plato dp ON p.id = dp.platos_id where dp.pedido_id = ?;"
            parametros = [(session["pedido"])]
            detalles = consultarBD(statement,parametros)
    return render_template('pedidos.html',titulo='Carrito de compras',platos = detalles)

@app.route('/Usuario/',methods=["GET","POST"])
def perfilUsuario():
    if es_usuario():
        if request.method == "POST":
            nombre = request.form.get("nombre")
            apellido = request.form.get("apellido")
            telefono = request.form.get("telefono")
            email = request.form.get("email")
            f_nacimiento = request.form.get("fecha_nacimiento")
            direccion = request.form.get("direccion")
            statement="UPDATE usuarios SET nombre = ?,apellido = ?,telefono = ?,correoelectronico = ?,fechanacimiento = ?,direccion = ? WHERE NIT = ?"
            parametros=(nombre,apellido,telefono,email,f_nacimiento,direccion,session['nit'])
            row_id = modificarBD(statement,parametros)
            limpiarMensajes()
            flash("usuarioActualizado")
        statement="SELECT nombre,apellido,correoelectronico, telefono, fechanacimiento, direccion FROM usuarios where NIT = ?"
        parametros=[(session["nit"])]
        datos = consultarBD(statement,parametros)
        return render_template('usuario_perfil.html',titulo='Perfil del usuario',datos=datos[0])
    limpiarMensajes()
    flash("login_failed")
    return redirect('/Login')

@app.route('/Usuario/Cuenta/',methods=["GET","POST"])
def configuracionUsuario():
    if es_usuario():
        if request.method == "POST":
            passwordActual = request.form.get("passwordActual")
            statement="SELECT contrasena FROM usuarios WHERE NIT = ?;"
            parametros=[(session["nit"])]
            passwordResult = consultarBD(statement,parametros)

            passwordActual = passwordActual.encode()
            limpiarMensajes()
            if bcrypt.checkpw(passwordActual,passwordResult[0][0]):
                nuevoPassword = request.form.get("nuevoPassword")
                nuevoPassword = nuevoPassword.encode()
                key = bcrypt.gensalt()
                passwordEncriptada = bcrypt.hashpw(nuevoPassword, key)
                statement="UPDATE usuarios SET contrasena = ? WHERE NIT = ?;"
                parametros=(passwordEncriptada,session["nit"])
                row_id = modificarBD(statement,parametros)
                flash("cambioPass")
            else:
                flash("fallido")
        return render_template('usuario_configuracion.html',titulo='Configuracion de cuenta')
    
    limpiarMensajes()
    flash("login_failed")
    return redirect('/Login')

@app.route('/Usuario/Pedidos/',methods=["GET","POST"])
def pedidosUsuarios():
    if es_usuario():
        statement="SELECT id,fecha,confirmado,total FROM pedido WHERE usuarios_nit=?;"
        parametros=(session["nit"],)
        pedidos = consultarBD(statement,parametros)
        for i in range(len(pedidos)):
            statement="SELECT imagen,nombre,cantidad,precio,id FROM detalles_plato as dp inner join platos as p ON dp.platos_id = p.id WHERE dp.pedido_id = ?;"
            parametros=(pedidos[i][0],)
            pedidos[i] = pedidos[i] + ((consultarBD(statement,parametros)),)
        if request.method == "POST":
            id_plato = request.form.get('id_plato')
            comentario = request.form.get('comentario')
            statement = "INSERT INTO comentarios (usuarios_nit,platos_id,comentario) VALUES (?,?,?);"
            parametros = (session["nit"],id_plato,comentario)
            row_id = modificarBD(statement,parametros)
        return render_template('usuario_pedidos.html',titulo='Pedidos del usuario',pedidos=pedidos)
    limpiarMensajes()
    flash('login_failed')
    return redirect('/Login')

@app.route('/Usuario/Comentarios/',methods=["GET","POST"])
def gestionComentarios():
    if es_usuario():
        statement="SELECT u.apellido,comentario,p.nombre as nombrePlato FROM comentarios as c inner join usuarios as u ON c.usuarios_nit = u.nit inner join platos as p ON p.id = c.platos_id WHERE u.nit = ?;"
        parametros=(session["nit"],)
        comentarios = consultarBD(statement,parametros)
        return render_template('usuario_comentarios.html',titulo='Gestionar comentarios',comentarios=comentarios)
    limpiarMensajes()
    flash('login_failed')
    return redirect('/Login')

@app.route('/Usuario/Administrador')
def ingresoAdministrador():
    return render_template('administrador.html',titulo='Administrador Dashboard')

@app.route('/Usuario/Administrador/GestionarUsuarios')
def gestionUsuarios():
    return render_template('gestionar_usuarios.html',titulo='Gestionar usuarios')

### Funciones
def consultarBD(query,params):
    if(query != ''):
        valid = False
        try:
            sqliteConnection = sqlite3.connect('./data/GoldStar.sqlite')
            cursor = sqliteConnection.cursor()
            if params:
                cursor.execute(query,params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            valid = True
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")
            if valid:
                return result
            else:
                return []

def modificarBD(statement,params):
    if(statement != ''):
        valid = False
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
            valid = True
        except sqlite3.Error as error:
            if  str(error) == 'UNIQUE constraint failed: detalles_plato.platos_id, detalles_plato.pedido_id':
                return "plato_registrado"
            print("Error while connecting to SQLite ", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
                print("The SQLite connection is closed")
            if valid:
                return row_id
            else:
                return None

def login_user(usuario,pedido):
    session["nit"] = usuario[0]
    session["nombre"] = usuario[1]
    session["usuario"] = usuario[2]
    session["tipo"] = usuario[4]
    session["pedido"] = pedido

def logout_user():
    session.pop("nit", None)
    session.pop("nombre", None)
    session.pop("usuario", None)
    session.pop("tipo", None)
    session.pop("pedido", None)

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

def limpiarMensajes():
    if '_flashes' in session:
        session['_flashes'].clear()

if __name__=="__main__":
    app.run(port=5000,debug=True)