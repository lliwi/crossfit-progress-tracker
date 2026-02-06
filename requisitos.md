# **Documento de Requerimientos: CrossFit PR Tracker**

Este documento detalla las especificaciones para el desarrollo de una aplicación web multiusuario destinada al seguimiento de marcas de fuerza (Personal Records) en CrossFit.

## **1\. Resumen Ejecutivo**

La aplicación permitirá a los atletas registrar sus levantamientos máximos (1RM y 3RM), visualizar su progreso a lo largo del tiempo y obtener automáticamente los porcentajes de carga necesarios para la programación de sus entrenamientos.

## **2\. Requerimientos Funcionales (RF)**

### **2.1 Gestión de Usuarios**

* **RF1.1 Registro e Inicio de Sesión:** Los usuarios deben poder crear una cuenta y autenticarse de forma segura.  
* **RF1.2 Privacidad de Datos:** Un usuario solo podrá acceder, editar o borrar sus propias marcas. No habrá visibilidad de datos entre usuarios.

### **2.2 Gestión de Marcas (Lifts)**

* **RF2.1 Registro de Ejercicios:** El usuario podrá seleccionar un ejercicio de una lista predefinida (ej. *Snatch, Clean & Jerk, Back Squat, Deadlift*) o añadir uno personalizado.  
* **RF2.2 Tipos de RM:** El sistema permitirá registrar específicamente marcas para:  
  * **1RM** (Una repetición máxima).  
  * **3RM** (Tres repeticiones máximas).  
* **RF2.3 Atributos del Registro:** Cada marca incluirá peso (kg/lb), fecha, ejercicio y tipo de RM.

* **RF3.1 Registro de skils desbloqueados:** El usuario podrá registar los skils de crossfit que ha desbloqueado, pull-ups, muscle-ups, handstand, etc.


### **2.3 Cálculos y Visualización**

* **RF3.1 Tabla de Porcentajes:** Al consultar un 1RM, la aplicación mostrará automáticamente el cálculo de:  
  * 60\%, 70\%, 80\% y $90\% del peso registrado.  
* **RF3.2 Histórico y Evolución:** Sección dedicada a mostrar una gráfica de línea por ejercicio para observar la progresión del peso en el tiempo.  
* **RF3.3 Dashboard:** Resumen de los últimos PRs obtenidos por el usuario.

## **3\. Requerimientos No Funcionales (RNF)**

* **RNF 3.1 Stack Tecnológico:** \- **Backend:** Python con **Flask**.  
La aplicaacipn ha de ser responsive y se usará mayoriritaramente desde el telefono.
  * **Base de Datos:** **PostgreSQL**.  
  * **Frontend:** HTML5, CSS (Tailwind o Bootstrap) y JavaScript (para gráficas).  
* **RNF 3.2 Despliegue:** La aplicación debe estar completamente "dockerizada" mediante docker-compose.  
* **RNF 3.3 Seguridad:** Uso de hashing para contraseñas (ej. BCrypt) y protección contra inyecciones SQL mediante un ORM (SQLAlchemy).

## **4\. Diseño de Base de Datos (Propuesta)**

### **Tabla: users**
3
* id: UUID / Serial (PK)  
* username: String (Unique)  
* password\_hash: String  
* email: String (Unique)

### **Tabla: exercises**

* id: Serial (PK)  
* name: String (ej. "Back Squat")

### **Tabla: lifts**

* id: Serial (PK)  
* user\_id: Integer (FK \-\> users.id)  
* exercise\_id: Integer (FK \-\> exercises.id)  
* weight: Float  
* reps\_type: Integer (Valores: 1 o 3\)  
* date: Date

## **5\. Arquitectura de Despliegue (Docker)**

El archivo docker-compose.yml deberá orquestar tres servicios:

1. **db:** Imagen oficial de postgres:latest.  
2. **web:** Imagen personalizada con el entorno de Python/Flask.  
3. **adminer (opcional):** Para gestión visual de la base de datos en desarrollo.

### **Ejemplo de Lógica de Cálculo (Python/Flask)**

def calculate\_percentages(rm\_weight):  
    percentages \= \[0.6, 0.7, 0.8, 0.9\]  
    return {f"{int(p\*100)}%": round(rm\_weight \* p, 2\) for p in percentages}  