from django.shortcuts import render , redirect , get_object_or_404
from django.http import JsonResponse , HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth import login , logout 
from django.contrib.auth.hashers import make_password , check_password
from django.contrib import messages
from  .models import Buyer , Seller , Product , Cart , Wishlist , Message , Newsletter ,Order , OrderItem
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Navbar  Functions
def home(request):
    return render(request,"pages/home.html")

def order(request):
    if not request.session.get("user_id"):
        return redirect("login")
    
    user = Buyer.objects.get(id = request.session.get("user_id"))
    order = Order.objects.filter(user=user).order_by('-id')

    context = {
        "orders":order
    }
    return render(request,"pages/order.html",context)

def menu(request):
    products = Product.objects.filter(product_status = "active")

    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "pages/menu.html", {"products": page_obj})

def about(request):
    return render(request,"pages/about.html")

def contact(request):
    if request.method == "POST":
        if request.session.get('user_id'):
            buyer = Buyer.objects.get(id=request.session['user_id'])
            subject = request.POST.get("subject")
            user_messages = request.POST.get("message")

            user_message = Message(
                user=buyer,
                name=buyer.user_name,
                email=buyer.user_email,
                subject=subject,
                message=user_messages
            )
            user_message.save()
            messages.success(request, "Message Sent Successfully.")
            return redirect("contact")
        else:
            messages.error(request, "Please login to send a message.")
            return redirect("login")

    return render(request,"pages/contact.html")

# Search Product Function 
def search_product(request):
    query = request.GET.get("q") or request.POST.get("search_product", "")

    products = []

    if query:
        products = Product.objects.filter(product_name__icontains=query)

        if not products.exists():
            messages.error(request, "No products found.")

    context = {
        "products": products,
        "search_query": query
    }

    return render(request, "search/search_product.html", context)

# Cart & Wishlist Functions 
def cart(request,):
    user_id = request.session.get("user_id")
    if not user_id:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Not logged in"}, status=403)
        return redirect("login")
    
    user = Buyer.objects.get(id=user_id)
    cart_items = Cart.objects.filter(user=user)

    total_amount = sum(item.subtotal() for item in cart_items)

    # -------------------------------
    # AJAX REQUEST → Return JSON
    # -------------------------------
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        items_json = []
        
        for c in cart_items:
            items_json.append({
                "id": c.pk,
                "product_name": c.product.product_name,
                "product_image": c.product.product_image.url,
                "price": float(c.price),
                "qty": c.qty,
                "subtotal": float(c.subtotal())
            })

        return JsonResponse({
            "items": items_json,
            "total_amount": float(total_amount)
        })

    # -------------------------------
    # Normal page render
    # -------------------------------
    context = {
        "user": user,
        "cart_items": cart_items,
        "total_amount": total_amount
    }

    return render(request, "shop/cart.html", context)


def add_to_cart(request,id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    user = Buyer.objects.get(id=user_id)
    product = Product.objects.get(id=id)

    existing_item = Cart.objects.filter(user=user,product=product).first()

    if existing_item:
        existing_item.qty += 1
        existing_item.save()
        messages.success(request,f"Updated quantity for {product.product_name}.")
    else:
        Cart.objects.create(
            user = user ,
            product = product,
            price = product.product_price ,
            qty = 1

        )
        messages.success(request, "Item added to your cart.")

    return redirect("cart")


def update_cart(request, id):
    if not request.session.get("user_id"):
        return JsonResponse({"error": "Not logged in"}, status=403)

    cart_item = Cart.objects.get(id=id)
    data = json.loads(request.body.decode("utf-8"))
    qty = int(data.get("qty"))

    if qty <= 0:
        cart_item.delete()
    else:
        cart_item.qty = qty
        cart_item.save()

    user = cart_item.user
    total_amount = sum(i.subtotal() for i in Cart.objects.filter(user=user))

    return JsonResponse({
        "subtotal": cart_item.subtotal() if qty > 0 else 0,
        "total_amount": float(total_amount)
    })


def remove_cart(request,id):
    cart_item = Cart.objects.get(id=id)
    user = cart_item.user
    cart_item.delete()

    total_amount = sum(i.subtotal() for i in Cart.objects.filter(user=user))

    return JsonResponse({"total_amount": float(total_amount)})

def empty_cart(request):
    user = Buyer.objects.get(id=request.session["user_id"])
    Cart.objects.filter(user=user).delete()

    return JsonResponse({"status": "success"})

def checkout(request):
    if not request.session.get("user_id"):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Not logged in"}, status=403)
        return redirect("login")

    user = Buyer.objects.get(id=request.session.get("user_id"))
    cart_items = Cart.objects.filter(user=user)

    if not cart_items.exists():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Cart is empty"}, status=400)
        messages.error(request, "Your Cart Is Empty!")
        return redirect("cart")

    # -----------------------------
    # AJAX POST → CREATE ORDER
    # -----------------------------
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))

        name = data.get("name")
        email = data.get("email")
        number = data.get("number")
        address = data.get("address")
        address_type = data.get("address_type")
        payment_method = data.get("method")


        # Create Order
        order = Order.objects.create(
            user=user,
            name=name,
            email=email,
            number=number,
            address=address,
            address_type=address_type,
            status="Processing",
            payment_status="Pending" if payment_method == "cod" else "Paid"
        )

        # Order Items
        for item in cart_items:
            product = item.product

            if product.product_stock < item.qty:
                return JsonResponse({
                    "error": f"Not enough stock for {product.product_name}"
                }, status=400)

            OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller,
                price=item.price,
                qty=item.qty,
            )

            product.product_stock -= item.qty
            product.save()

        cart_items.delete()

        return JsonResponse({
            "success": True,
            "redirect_url": f"/order_success/{order.id}/"
        })

    # -----------------------------
    # NORMAL PAGE RENDER
    # -----------------------------
    total_amount = sum(item.subtotal() for item in cart_items)

    return render(request, "shop/checkout.html", {
        "user": user,
        "cart_items": cart_items,
        "total_amount": total_amount
    })

def order_success(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    order_items = order.items.all()   # related_name="items"

    total_amount = sum(item.total_price() for item in order_items)

    return render(request, "shop/order_success.html", {
        "order": order,
        "order_items": order_items,
        "total_amount": total_amount
    })

def wishlist(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)
    items = Wishlist.objects.filter(user=user)

    return render(request, "shop/wishlist.html", {"items": items})

def add_to_wishlist(request, id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)
    product = Product.objects.get(id=id)

    Wishlist.objects.get_or_create(
        user=user,
        product=product,
        defaults={"price": product.product_price}
    )

    return redirect("wishlist")

def toggle_wishlist(request, id):

    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Login required"}, status=403)

    user = Buyer.objects.get(id=user_id)
    product = Product.objects.get(id=id)

    wishlist_item = Wishlist.objects.filter(user=user, product=product)

    if wishlist_item.exists():
        wishlist_item.delete()
        return JsonResponse({"status": "removed"})
    else:
        Wishlist.objects.create(user=user, product=product, price=product.product_price)
        return JsonResponse({"status": "added"})

def remove_wishlist(request, id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)
    Wishlist.objects.filter(id=id, user=user).delete()

    return redirect("wishlist")

  #  Views Function 

def view_product(request, id):
    product = get_object_or_404(Product, id=id)

    return render(request, "shop/views/view_product.html", {
        "product": product
    })

def view_order(request, id):
    order = get_object_or_404(Order, id=id)
    order_items = order.items.all()

    # Calculate total amount
    total_amount = sum(item.total_price() for item in order_items)

    return render(request, "shop/views/view_order.html", {
        "order": order,
        "order_items": order_items,
        "total_amount": total_amount,
    })

def cancel_order(request, id):

    order = get_object_or_404(Order, id=id)

    # update status
    order.status = "canceled"
    order.payment_status = "pending"
    order.save()

    # restore product stock
    for item in order.items.all():
        product = item.product
        product.product_stock += item.qty
        product.save()

    messages.success(request, "Order canceled successfully!")

    return redirect("view_order", id=id)



# Profile Functions
def profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)

    return render(request, "user/profile.html", {
        "user": user
    })

def update_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)

    if request.method == "POST":
        user.user_name = request.POST.get("user_name")
        user.user_email = request.POST.get("user_email")
        user.user_password = request.POST.get("user_password")   # plain password (you can hash later)

        if "user_image" in request.FILES:
            user.user_image = request.FILES["user_image"]

        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    return render(request, "user/update_profile.html", {
        "user": user
    })

def user_messages(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    user = Buyer.objects.get(id=user_id)
    messages_list = Message.objects.filter(user=user)

    return render(request, "user/messages.html", {
        "messages_list": messages_list
    })


# Authenticate Functions
def user_register(request):
    if request.method == "POST":
        username = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')
        profile_image = request.FILES.get('profile_image')

        if password != cpassword:
            messages.error(request,"Passwords do not match!")
            return redirect("register")
        
        if Buyer.objects.filter(user_email = email).exists():
            messages.error(request,"Email Already exists!")
            return redirect("register")
         
         # Image Validation
        if profile_image:
            valid_extensions = ['jpg','jpeg','png','gif'] 
            file_extension = profile_image.name.split('.')[-1].lower()
            if file_extension not in valid_extensions:
                messages.error(request,"Invalid file format! Only JPG, JPEG, PNG and GIF allowed.")
                return redirect("register")
            
        
        user = Buyer(
            user_name = username,
            user_email = email,
            user_password = make_password(password),
            user_image = profile_image if profile_image else "user_profile.jpg"
        )
        user.save()

        request.session['user_id'] = user.pk
        request.session['user_name'] = user.user_name
        request.session['user_email'] = user.user_email
        request.session['user_image'] = str(user.user_image)

        messages.success(request, f"Welcome {user.user_name}! Account created successfully.")
        return redirect("home") 
    
    return render(request,"user/auth/register.html")

def user_login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user =  Buyer.objects.get(user_email = email)
        except Buyer.DoesNotExist:
            messages.error(request,"Email not registered!")
            return redirect("login")
        
        if check_password(password, user.user_password):

            request.session['user_id'] = user.pk
            request.session['user_name'] = user.user_name
            request.session['user_email'] = user.user_email
            request.session['user_image'] = str(user.user_image)

            messages.success(request,f"Welcome Back ,{user.user_name}")
            return redirect("home")
        else :
            messages.error(request, "Incorrect password!")
            return redirect("login")
            
    return render(request,"user/auth/login.html")

def user_logout(request):
    request.session.flush()
    messages.success(request,"Logout Successfully!")
    return redirect("login")

def download_invoice(request, order_id):
    order = Order.objects.get(id=order_id)
    items = order.items.all()

    # Create the PDF response
    response_pdf = HttpResponse(content_type="application/pdf")
    response_pdf["Content-Disposition"] = f'attachment; filename="Invoice_{order.id}.pdf"'

    # Initialize PDF canvas
    p = canvas.Canvas(response_pdf, pagesize=A4)
    width, height = A4

    y = height - 50

    # ============= HEADER ==============
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, y, "Blue Sky Summer")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(50, y, "Customer Invoice")
    y -= 20

    p.line(50, y, width - 50, y)
    y -= 30

    # ============= ORDER INFO ==============
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Order ID: #{order.id}")
    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Name: {order.name}")
    y -= 20
    p.drawString(50, y, f"Email: {order.email}")
    y -= 20
    p.drawString(50, y, f"Phone: {order.number}")
    y -= 20
    p.drawString(50, y, f"Address: {order.address}")
    y -= 20
    p.drawString(50, y, f"Payment Status: {order.payment_status}")
    y -= 30

    p.line(50, y, width - 50, y)
    y -= 40

    # ============= TABLE HEADER ==============
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Product")
    p.drawString(250, y, "Qty")
    p.drawString(320, y, "Price")
    p.drawString(400, y, "Total")
    y -= 20

    p.line(50, y, width - 50, y)
    y -= 25

    # ============= ORDER ITEMS ==============
    p.setFont("Helvetica", 12)
    total = 0

    for item in items:
        p.drawString(50, y, item.product.product_name)
        p.drawString(250, y, str(item.qty))
        p.drawString(320, y, f"${item.price}")
        p.drawString(400, y, f"${item.total_price()}")
        total += item.total_price()

        y -= 20

        if y < 100:
            p.showPage()
            y = height - 50

    # ============= TOTAL AMOUNT ==============
    y -= 20
    p.line(50, y, width - 50, y)
    y -= 30

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, f"Grand Total: ${total}")

    # Finish PDF
    p.showPage()
    p.save()

    return response
