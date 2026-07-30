from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from models import db, Book, Member, Transaction, User
from datetime import date, datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SECRET_KEY'] = 'change-this-secret-key'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


FINE_PER_DAY = 5
LOAN_PERIOD_DAYS = 14


# ==============================
# Authentication
# ==============================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':

        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'error')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('signup'))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully. Please log in.', 'success')

        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        flash('Invalid username or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():

    if request.method == 'POST':
        logout_user()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('login'))

    return render_template('logout.html')


# ==============================
# Landing Page
# ==============================

@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/features/books')
def feature_books():
    return render_template('feature_books.html')


@app.route('/features/members')
def feature_members():
    return render_template('feature_members.html')


@app.route('/features/dashboard-preview')
def feature_dashboard_preview():
    return render_template('feature_dashboard.html')


# ==============================
# Dashboard
# ==============================

@app.route('/dashboard')
@login_required
def dashboard():
    total_books = Book.query.count()
    total_copies = db.session.query(db.func.sum(Book.total_copies)).scalar() or 0
    available_copies = db.session.query(db.func.sum(Book.available_copies)).scalar() or 0
    total_members = Member.query.count()
    issued_count = Transaction.query.filter_by(status='Issued').count()

    overdue_count = Transaction.query.filter(
        Transaction.status == 'Issued',
        Transaction.due_date < date.today()
    ).count()

    return render_template(
        'index.html',
        total_books=total_books,
        total_copies=total_copies,
        available_copies=available_copies,
        total_members=total_members,
        issued_count=issued_count,
        overdue_count=overdue_count
    )


# ==============================
# Books
# ==============================

@app.route('/books')
@login_required
def books():
    query = request.args.get('q', '').strip()

    if query:
        books_list = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%'))
        ).all()
    else:
        books_list = Book.query.all()

    return render_template(
        'books.html',
        books=books_list,
        query=query
    )


@app.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():

    if request.method == 'POST':

        title = request.form['title'].strip()
        author = request.form['author'].strip()
        isbn = request.form['isbn'].strip()
        category = request.form['category'].strip()
        total_copies = int(request.form['total_copies'])

        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            category=category,
            total_copies=total_copies,
            available_copies=total_copies
        )

        db.session.add(book)
        db.session.commit()

        flash(f'Book "{title}" added successfully.', 'success')

        return redirect(url_for('books'))

    return render_template('add_book.html')


@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):

    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':

        old_total = book.total_copies
        new_total = int(request.form['total_copies'])
        diff = new_total - old_total

        book.title = request.form['title'].strip()
        book.author = request.form['author'].strip()
        book.isbn = request.form['isbn'].strip()
        book.category = request.form['category'].strip()

        book.total_copies = new_total
        book.available_copies = max(
            0,
            book.available_copies + diff
        )

        db.session.commit()

        flash('Book updated successfully.', 'success')

        return redirect(url_for('books'))

    return render_template(
        'add_book.html',
        book=book
    )


@app.route('/books/delete/<int:book_id>')
@login_required
def delete_book(book_id):

    book = Book.query.get_or_404(book_id)

    active_loans = Transaction.query.filter_by(
        book_id=book.id,
        status='Issued'
    ).count()

    if active_loans > 0:
        flash(
            'Cannot delete a book that currently has copies issued.',
            'error'
        )
    else:
        db.session.delete(book)
        db.session.commit()
        flash('Book deleted.', 'success')

    return redirect(url_for('books'))
# ==============================
# Members
# ==============================

@app.route('/members')
@login_required
def members():
    query = request.args.get('q', '').strip()

    if query:
        members_list = Member.query.filter(
            (Member.name.ilike(f'%{query}%')) |
            (Member.email.ilike(f'%{query}%'))
        ).all()
    else:
        members_list = Member.query.all()

    return render_template(
        'members.html',
        members=members_list,
        query=query
    )


@app.route('/members/add', methods=['GET', 'POST'])
@login_required
def add_member():

    if request.method == 'POST':

        member = Member(
            name=request.form['name'].strip(),
            email=request.form['email'].strip(),
            phone=request.form['phone'].strip(),
            membership_date=date.today()
        )

        db.session.add(member)
        db.session.commit()

        flash(
            f'Member "{member.name}" registered.',
            'success'
        )

        return redirect(url_for('members'))

    return render_template('add_member.html')


@app.route('/members/delete/<int:member_id>')
@login_required
def delete_member(member_id):

    member = Member.query.get_or_404(member_id)

    active_loans = Transaction.query.filter_by(
        member_id=member.id,
        status='Issued'
    ).count()

    if active_loans > 0:
        flash(
            'Cannot delete a member who currently has books issued.',
            'error'
        )
    else:
        db.session.delete(member)
        db.session.commit()
        flash('Member removed.', 'success')

    return redirect(url_for('members'))


# ==============================
# Issue Book
# ==============================

@app.route('/issue', methods=['GET', 'POST'])
@login_required
def issue_book():

    if request.method == 'POST':

        book_id = int(request.form['book_id'])
        member_id = int(request.form['member_id'])

        issue_date = datetime.strptime(
            request.form['issue_date'],
            '%Y-%m-%d'
        ).date()

        due_date = datetime.strptime(
            request.form['due_date'],
            '%Y-%m-%d'
        ).date()

        if due_date < issue_date:
            flash(
                'Due date cannot be earlier than issue date.',
                'error'
            )
            return redirect(url_for('issue_book'))

        book = Book.query.get_or_404(book_id)

        if book.available_copies < 1:
            flash(
                'No copies of this book are currently available.',
                'error'
            )
            return redirect(url_for('issue_book'))

        transaction = Transaction(
            book_id=book_id,
            member_id=member_id,
            issue_date=issue_date,
            due_date=due_date,
            status='Issued'
        )

        book.available_copies -= 1

        db.session.add(transaction)
        db.session.commit()

        flash(
            'Book issued successfully.',
            'success'
        )

        return redirect(url_for('transactions'))

    available_books = Book.query.filter(
        Book.available_copies > 0
    ).all()

    all_members = Member.query.all()

    return render_template(
        'issue_book.html',
        books=available_books,
        members=all_members
    )


# ==============================
# Return Book
# ==============================

@app.route('/return/<int:transaction_id>')
@login_required
def return_book(transaction_id):

    transaction = Transaction.query.get_or_404(transaction_id)

    if transaction.status == 'Returned':
        flash(
            'This book has already been returned.',
            'error'
        )
        return redirect(url_for('transactions'))

    transaction.return_date = date.today()
    transaction.status = 'Returned'

    if transaction.return_date > transaction.due_date:

        days_late = (
            transaction.return_date -
            transaction.due_date
        ).days

        transaction.fine_amount = (
            days_late * FINE_PER_DAY
        )

    else:
        transaction.fine_amount = 0

    transaction.book.available_copies += 1

    db.session.commit()

    if transaction.fine_amount > 0:

        flash(
            f'Book returned successfully. Fine: ₹{transaction.fine_amount}',
            'error'
        )

    else:

        flash(
            'Book returned successfully.',
            'success'
        )

    return redirect(url_for('transactions'))
# ==============================
# Transactions
# ==============================

@app.route('/transactions')
@login_required
def transactions():

    all_transactions = Transaction.query.order_by(
        Transaction.issue_date.desc()
    ).all()

    today = date.today()

    return render_template(
        'transactions.html',
        transactions=all_transactions,
        today=today
    )


# ==============================
# Run Application
# ==============================

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(
        debug=True
    )
