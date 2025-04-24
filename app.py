from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Book, Author, Category, Loan, BookCategory , BookRequest
from config import Config
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_admin():
    return current_user.is_authenticated and current_user.role == 'admin'

@app.context_processor
def inject_stats():
    stats = {}
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            stats.update({
                'book_count': Book.query.count(),
                'user_count': User.query.count(),
                'active_loans': Loan.query.filter_by(status='active').count()
            })
        else:
            stats.update({
                'active_loan_count': Loan.query.filter_by(
                    user_id=current_user.id,
                    status='active'
                ).count()
            })
    return stats

@app.route('/')
def index():
    return render_template('index.html')

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Geçersiz email veya şifre', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first():
            flash('Bu email zaten kayıtlı', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(name=name, email=email, role='user')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Kayıt başarılı. Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')
    
@app.route("/all-books", methods=["GET"])
@login_required
def all_books():
    books = Book.query.all()
    return render_template("user/all_books.html", books=books)

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        secret_code = request.form.get('secret_code')
        if secret_code != "ADMIN123":
            flash('Geçersiz admin kayıt kodu', 'danger')
            return redirect(url_for('admin_register'))
            
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(email=email).first():
            flash('Bu email zaten kayıtlı', 'danger')
            return redirect(url_for('admin_register'))
        
        new_user = User(name=name, email=email, role='admin')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Admin kaydı başarılı. Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/admin_register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if is_admin():
        return render_template('admin/dashboard.html')
    return render_template('user/dashboard.html')

# Admin Routes
@app.route("/admin/books", methods=["GET", "POST"])
@login_required
def admin_books():
    if not is_admin():
        abort(403)
    books = Book.query.all()
    authors = Author.query.all()
    return render_template('admin/books.html', books=books, authors=authors)

@app.route('/admin/books/add', methods=['POST'])
@login_required
def add_book():
    if not is_admin():
        abort(403)

    title = request.form['title']
    isbn = request.form['isbn']
    author_name = request.form['author_name']
    publication_year = request.form.get('publication_year')
    page_count = request.form.get('page_count')
    shelf_number = request.form.get('shelf_number')

    # Yazar var mı kontrol et, yoksa oluştur
    author = Author.query.filter_by(name=author_name).first()
    if not author:
        author = Author(name=author_name)
        db.session.add(author)
        db.session.commit()  # Yeni yazarı kaydet

    # Kitabı oluştur
    new_book = Book(
        title=title,
        isbn=isbn,
        author_id=author.id,
        publication_year=int(publication_year) if publication_year else None,
        page_count=int(page_count) if page_count else None,
        shelf_number=shelf_number
    )

    try:
        db.session.add(new_book)
        db.session.commit()
        flash('Kitap başarıyla eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')

    return redirect(url_for('admin_books'))



@app.route('/admin/books/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(id):
    if not is_admin():
        abort(403)

    book = Book.query.get_or_404(id)

    if request.method == 'POST':
        book.title = request.form['title']
        book.isbn = request.form['isbn']
        book.publication_year = request.form.get('publication_year')
        book.page_count = request.form.get('page_count')
        book.shelf_number = request.form.get('shelf_number')

        # Yeni: Formdan gelen yazar adı
        author_name = request.form['author'].strip()

        # Aynı isimde yazar var mı kontrol et
        author = Author.query.filter_by(name=author_name).first()
        if not author:
            author = Author(name=author_name)
            db.session.add(author)
            db.session.commit()

        book.author_id = author.id

        db.session.commit()
        flash('Kitap başarıyla güncellendi', 'success')
        return redirect(url_for('admin_books'))

    authors = Author.query.all()
    return render_template('admin/edit_book.html', book=book, authors=authors)

@app.route("/admin/books/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)

    # Kitapla ilişkili kategori bağlantılarını sil
    for category in book.categories:
        db.session.delete(category)

    db.session.delete(book)
    db.session.commit()

    flash("Kitap silindi.", "success")
    return redirect(url_for("admin_books"))

@app.route('/admin/users')
@login_required
def admin_users():
    if not is_admin():
        abort(403)
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    if not is_admin():
        abort(403)
    
    user = User.query.get_or_404(id)

    if user == current_user:
        flash('Kendi hesabınızı silemezsiniz', 'danger')
        return redirect(url_for('admin_users'))

    # Kullanıcıya ait tüm loan kayıtlarını sil
    Loan.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()
    flash('Kullanıcı başarıyla silindi', 'success')
    return redirect(url_for('admin_users'))


# User Routes
@app.route('/user/search', methods=['GET', 'POST'])
@login_required
def search_books():
    if request.method == 'POST':
        query = request.form['query']
        search_by = request.form['search_by']
        
        if search_by == 'title':
            books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
        elif search_by == 'author':
            books = Book.query.join(Author).filter(Author.name.ilike(f'%{query}%')).all()
        else:
            books = Book.query.join(BookCategory).join(Category).filter(Category.name.ilike(f'%{query}%')).all()
        
        return render_template('user/search.html', books=books, query=query)
    return render_template('user/search.html')

@app.route('/user/loans')
@login_required
def my_loans():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.loan_date.desc()).all()
    return render_template('user/loans.html', loans=loans, datetime=datetime)

@app.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)

    if book.status != 'available':
        flash('Bu kitap şu anda ödünç alınamaz', 'danger')
        return redirect(url_for('search_books'))

    # Kullanıcı için onaylı bir istek var mı?
    approved_request = BookRequest.query.filter_by(
        user_id=current_user.id,
        book_id=book_id,
        status='approved'
    ).first()

    if not approved_request:
        flash('Bu kitabı ödünç almak için admin onayı gereklidir.', 'warning')
        return redirect(url_for('search_books'))

    loan = Loan(
        user_id=current_user.id,
        book_id=book.id,
        due_date=datetime.utcnow() + timedelta(days=14)
    )

    book.status = 'borrowed'

    db.session.add(loan)
    db.session.commit()

    flash('Kitap başarıyla ödünç alındı', 'success')
    return redirect(url_for('my_loans'))


@app.route('/request_book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_request = BookRequest(user_id=session['user_id'], book_id=book_id)
    db.session.add(new_request)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/return/<int:loan_id>', methods=['POST'])
@login_required
def return_book(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    
    if loan.user_id != current_user.id and not is_admin():
        abort(403)
    
    loan.return_date = datetime.utcnow()
    loan.status = 'returned'
    loan.book.status = 'available'
    
    db.session.commit()
    
    flash('Kitap başarıyla iade edildi', 'success')
    return redirect(url_for('my_loans' if current_user.role == 'user' else 'admin_books'))



# Kitap isteklerini görüntüle
@app.route('/admin/requests')
@login_required
def view_requests():
    if not current_user.is_admin:  # Admin kontrolü varsa
        flash("Bu sayfaya erişim izniniz yok", "danger")
        return redirect(url_for('dashboard'))

    requests = BookRequest.query.all()
    return render_template('admin_requests.html', requests=requests)

# Admin kitap talebini onaylar
@app.route('/admin/approve_request/<int:request_id>')
@login_required
def approve_request(request_id):
    if not current_user.is_admin:
        flash("Bu işlemi yapamazsınız", "danger")
        return redirect(url_for('dashboard'))

    req = BookRequest.query.get_or_404(request_id)
    req.status = 'approved'
    db.session.commit()

    flash("İstek onaylandı!", "success")
    return redirect(url_for('view_requests'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Örnek veriler
        if not User.query.first():
            # Admin kullanıcısı
            admin = User(
                name='Admin',
                email='admin@kutuphane.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Normal kullanıcı
            user = User(
                name='Test Kullanıcı',
                email='kullanici@kutuphane.com',
                role='user'
            )
            user.set_password('test123')
            db.session.add(user)
            
            # Yazarlar
            yazarlar = [
                Author(name='Yaşar Kemal', bio='Ünlü Türk yazar'),
                Author(name='Orhan Pamuk', bio='Nobel ödüllü yazar'),
                Author(name='Sabahattin Ali', bio='Türk edebiyatının klasikleri')
            ]
            db.session.add_all(yazarlar)
            
            # Kategoriler
            kategoriler = [
                Category(name='Roman', description='Kurgusal eserler'),
                Category(name='Şiir', description='Şiir kitapları'),
                Category(name='Bilim Kurgu', description='Bilim kurgu eserleri')
            ]
            db.session.add_all(kategoriler)
            
            db.session.commit()
            
            # Kitaplar
            kitaplar = [
                Book(
                    title='İnce Memed',
                    isbn='9789750806623',
                    author_id=1,
                    publication_year=1955,
                    page_count=436,
                    shelf_number='RA-101'
                ),
                Book(
                    title='Kara Kitap',
                    isbn='9789754700114',
                    author_id=2,
                    publication_year=1990,
                    page_count=465,
                    shelf_number='RA-102'
                ),
                Book(
                    title='Kürk Mantolu Madonna',
                    isbn='9789753638029',
                    author_id=3,
                    publication_year=1943,
                    page_count=160,
                    shelf_number='RA-103'
                )
            ]
            db.session.add_all(kitaplar)
            db.session.commit()
            
            # Kitap-kategori ilişkileri
            kitap_kategoriler = [
                BookCategory(book_id=1, category_id=1),
                BookCategory(book_id=2, category_id=1),
                BookCategory(book_id=3, category_id=1),
                BookCategory(book_id=2, category_id=3)
            ]
            db.session.add_all(kitap_kategoriler)
            db.session.commit()
    
    app.run(host="0.0.0.0", port=5000, debug=True)
