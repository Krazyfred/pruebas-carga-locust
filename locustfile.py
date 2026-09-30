from locust import HttpUser, task, between, events
import random
import time

#Meter usuarios en base de datos
# --- Configuración ---
# Usuarios de prueba (deben existir previamente en la base de datos de la aplicación)
TEST_USERS = [
    {"email": "usuario1@example.com", "password": "cambiar_por_password_de_prueba", "name": "usuario1"},
    {"email": "usuario2@example.com", "password": "cambiar_por_password_de_prueba", "name": "usuario2"},
]

PRODUCT_IDURLS = [
    "poster-cosmos-abstracto", "poster-montanas-serenas", "poster-geometria-urbana"
]

PRODUCTS_TO_PUT_OR_PATCH = ["poster-fauna-fantastica", "poster-codigo-binario"]

PRODUCT_IDS = [1, 2, 3]

CREATED_ORDER_IDS = []

#Clas que implementa los tests locust
class WebStoreUser(HttpUser):
    wait_time = between(1, 3) # Tiempo de espera entre tareas
    user_email = None
    my_created_order_ids = []

    #Nos aseguramos de que el usuario este logueado
    #Realiza POST a login API
    def on_start(self):
        credentials = random.choice(TEST_USERS)
        self.user_email = credentials["email"]
        login_url = "/api/login"
        self.my_created_order_ids = []
        print(f"Usuario Locust iniciando sesión como: {self.user_email}")

        try:
            login_payload = {
                "username":self.user_email,
                "password":credentials["password"]
            }
            with self.client.post(
                login_url,
                json = login_payload,
                name = "/api/login"
            )as response:
                print(f"Usuario {self.user_email}: Login exitoso (HTTP {response.status_code}).")

        except Exception as e:
            print(f"Usuario {self.user_email}: FALLO en Login - {e}. Respuesta: {response.text if 'response' in locals() else 'N/A'}")
    
    #referencia de creación de test locust
    #def nombre_funcion(self):
        #logica necesaria para el endpoint (como definición de variables/obtención de respuestas)
        #self.client.<metodo>("url")


    # Tareas públicas, aquellas en las que el usuario no necesita estar logueado
    #/api/productos
    @task(10)
    def view_products(self):
        print(f"Usuario {self.user_email or 'Anónimo'}: Viendo lista de productos")
        self.client.get("/api/productos")

    #/api/productos/{product_idurl}
    #Por esta funcion inicializamos previamente PRODUCT_IDURLS
    @task(5)
    def view_product_detail(self):
        product_idurl = random.choice(PRODUCT_IDURLS)
        print(f"Usuario {self.user_email or 'Anónimo'}: Viendo detalles de {product_idurl}")
        self.client.get(f"/api/productos/{product_idurl}", name="/api/productos/[idurl]")

    #/api/menu
    @task(3)
    def view_menu(self):
        print(f"Usuario {self.user_email or 'Anónimo'}: Viendo menú")
        self.client.get("/api/menu") 

    # Tareas que requieren de autenticación para ser realizadas
    #/api/cart/add
    @task(8)
    def add_item_to_cart(self):
        if not self.user_email: return 
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 2)
        print(f"Usuario {self.user_email}: Añadiendo producto {product_id} (x{quantity}) al carrito")
        with self.client.post(
            "/api/cart/add",
            json={"product_id": product_id, "quantity": quantity},catch_response=True
        ) as response:
            print(f"Usuario {self.user_email} -> /api/cart/add Checkout failed: Status={response.status_code}, Text='{response.text[:100]}...'")
            error_data = response.json()
            if "No hay suficiente stock disponible" in error_data.get("message", ""):
                response.success()
                print(f"Usuario {self.user_email}: Stock insuficiente para el producto {product_id}.")

    #/api/carrito
    @task(4)
    def view_cart(self):
        if not self.user_email: return
        print(f"Usuario {self.user_email}: Viendo carrito")
        self.client.get("/api/carrito")

    #/api/checkout
    #Contiene logica extra creando CREATED_ORDER_IDS para que despues /api/pedidos/{order_id} pueda hacer el get de un pedido correcto
    @task(1)
    def checkout(self):
        with self.client.get("/api/carrito", catch_response=True, name="/api/carrito") as cart_response:
            if cart_response.status_code == 200:
                try:
                    cart_data = cart_response.json()
                    if cart_data.get("cart_items") and len(cart_data.get("cart_items")) > 0:
                        with self.client.post("/api/checkout", catch_response=True, name="/api/checkout") as checkout_response:
                            if checkout_response.status_code == 200 or checkout_response.status_code == 201: # Tu API devuelve 200
                                try:
                                    order_data = checkout_response.json()
                                    new_order_id = order_data.get('order_id')
                                    if new_order_id:
                                        if hasattr(self, 'my_created_order_ids'):
                                            self.my_created_order_ids.append(new_order_id)
                                        checkout_response.success()
                                    else:
                                        checkout_response.failure(f"Checkout success ({checkout_response.status_code}) but no order_id")
                                except ValueError:
                                    checkout_response.failure(f"Checkout success ({checkout_response.status_code}) but invalid JSON response")
                            else:
                                checkout_response.failure(f"Checkout POST failed with status {checkout_response.status_code}")
                    else:
                        pass
                except ValueError:
                    cart_response.failure("Pre-checkout: GET /api/carrito invalid JSON response")
            else:
                # El GET a /api/carrito falló
                cart_response.failure(f"Pre-checkout: GET /api/carrito failed status {cart_response.status_code}")

    #/api/pedidos
    @task(3)
    def view_orders(self):
        if not self.user_email: return
        print(f"Usuario {self.user_email}: Viendo lista de pedidos")
        self.client.get("/api/pedidos")

    #/api/pedidos/{order_id}
    @task(2)
    def view_order_detail(self):
        if not self.user_email or not self.my_created_order_ids:
             return
        order_id = random.choice(self.my_created_order_ids)
        print(f"Usuario {self.user_email}: Viendo detalles del pedido {order_id}")
        self.client.get(f"/api/pedidos/{order_id}", name="/api/pedidos/[order_id]")

    #/api/carrito/vaciar
    @task(1)
    def empty_cart(self):
         if not self.user_email: return
         print(f"Usuario {self.user_email}: Vaciando carrito")
         self.client.delete("/api/carrito/vaciar")

    #/api/registro
    @task(1) 
    def register_new_user(self):
        timestamp = int(time.time() * 1000)
        new_email = f"locust_user_{timestamp}@example.com"
        new_name = f"LocustUser_{timestamp}"
        new_password = "password123"
        print(f"Intentando registrar nuevo usuario: {new_email}")
        self.client.post(
            "/api/registro", 
            data={
                "email": new_email,
                "usuario": new_name,
                "contrasenya": new_password
            }
        )
    
    #/api/productos/{product_idurl}
    @task(1)
    def update_product_put(self):
        product_idurl_to_update = random.choice(PRODUCTS_TO_PUT_OR_PATCH)
        timestamp = int(time.time())
        updated_data = {
            "title": f"Póster Actualizado {timestamp}",
            "description": f"Descripción actualizada el {time.ctime(timestamp)}.",
            "artist": f"Artista {random.choice(['A', 'B', 'C'])}",
            "price": round(random.uniform(10.0, 50.0), 2),
            "stock": random.randint(5, 100),
            "image_url": f"/static/images/updated_poster_{timestamp}.jpg"
        }
        self.client.put(
            f"/api/productos/{product_idurl_to_update}",
            json=updated_data,
            name="/api/productos/[idurl] PUT"
        )

    #/api/productos/{product_idurl}
    @task(2)
    def update_product_patch(self):
        product_idurl_to_update = random.choice(PRODUCTS_TO_PUT_OR_PATCH)

        patch_data = {}
        if random.choice([True, False]):
            patch_data["price"] = round(random.uniform(15.0, 45.0), 2)
        if random.choice([True, False]):
            patch_data["stock"] = random.randint(1, 75)
        if random.choice([True, False]) and "price" not in patch_data and "stock" not in patch_data:
             patch_data["title"] = f"Título Parcialmente Actualizado {int(time.time())}"
        
        if not patch_data:
            patch_data["stock"] = random.randint(10, 60)

        self.client.patch(
            f"/api/productos/{product_idurl_to_update}",
            json=patch_data,
            name="/api/productos/[idurl] PATCH"
        )
