from app import application
from app import *
from app.models import *
import uuid
from flask import session, Response, jsonify
import datetime
from flask_restful import Resource, Api
from flask_apispec.views import MethodResource
from marshmallow import Schema, fields
from flask_apispec import marshal_with, doc, use_kwargs
import json

class SignUpRequest(Schema):
    username = fields.Str(default = "username")
    password = fields.Str(default = "password")
    address = fields.Str(default = "address")
    phone_number = fields.Str(default = "+91 99999 00000")
    email_id = fields.Str(default = "exampla@abc.com")

class LoginRequest(Schema):
    username = fields.Str(default = "username")
    password = fields.Str(default = "password")

class StocksRequest(Schema):
    stock_id = fields.Str(default="stock_id")
    units = fields.Int(default = 0)

class StocksListResponse(Schema):
    stocks = fields.List(fields.Dict())

class APIResponse(Schema):
    message = fields.Str(default = "Success")

class TransactionResponse(Schema):
    transactions = fields.List(fields.Dict())




class SignUpAPI(MethodResource, Resource):
    @doc(description="Sign Up API", tags=['SignUp API'])
    @use_kwargs(SignUpRequest, location=('json'))
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            user = Users(
                uuid.uuid4(),
                kwargs['username'],
                kwargs['password'],
                kwargs['address'],
                kwargs['phone_number'],
                kwargs['email_id'],
                1,
                datetime.datetime.utcnow())
            db.session.add(user)
            db.session.commit()
            return APIResponse().dump(dict(message="User got registered successfully")), 201
        
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message=f'Not able to register user: {str(e)}')), 400
        
api.add_resource(SignUpAPI, '/signup')
docs.register(SignUpAPI)


class LoginAPI(MethodResource, Resource):
    @doc(description='Login API', tags=['Login API'])
    @use_kwargs(LoginRequest, location=('json'))
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            user = Users.query.filter_by(username=kwargs['username'], password = kwargs['password']).first()
            if user:
                print('logged in')
                session['user_id'] = user.user_id
                print(f'User id :  {str(session["user_id"])}')
                return APIResponse().dump(dict(message='User got logged in successfully'))
            else:
                return APIResponse().dump(dict(message = 'User Not Found')), 404
            
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message=f'Not able to login user: {str(e)}')), 400
        
api.add_resource(LoginAPI, '/login')
docs.register(LoginAPI)


class LogoutAPI(MethodResource, Resource):
    @doc(decription='LogOut API', tags=['Logout API'])
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            if session['user_id']:
                session['user_id'] =  None
                print('logged out')
                return APIResponse().dump(dict(message='User got logged out successfully')), 200
            else:
                print('user not found')
                return APIResponse().dump(dict(message='User is not logged in')), 401
            
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Not able to logout user: {str(e)}')), 400
        
api.add_resource(LogoutAPI, '/logout')
docs.register(LogoutAPI)


class StocksListAPI(MethodResource, Resource):
    @doc(description='Stocks List API', tags=['Stocks API'])
    @marshal_with(StocksListResponse)
    def get(self):
        try:
            stocks = Stocks.query.all()
            stocks_list = list()
            for stock in stocks:
                stock_dict = {}
                stock_dict['stock_id'] = stock.stock_id
                stock_dict['stock_name'] = stock.stock_name
                stock_dict['stock_description'] = stock.stock_description
                stock_dict['balance_units'] = stock.balance_units
                stock_dict['exercise_price'] = stock.exercise_price
                stock_dict['currency'] = stock.currency

                stocks_list.append(stock_dict)
            print(stocks_list)
            return StocksListResponse().dump(dict(stocks = stocks_list)), 200
        
        except Exception as e:
            return APIResponse.dump(dict(message = f'Not able to list stocks: {str(e)}')), 400
        
api.add_resource(StocksListAPI, '/stocks')
docs.register(StocksListAPI)


class BuyStocksAPI(MethodResource, Resource):
    @doc(description = 'Buy Stocks API', tags=['BuyStocks API'])
    @use_kwargs(StocksRequest, location=('json'))
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            if session['user_id']:
                stock_id = kwargs['stock_id']
                units = kwargs['units']
                if units <=0:
                    return APIResponse().dump(dict(message = 'Units must be more than 0')), 400
                stock = Stocks.query.filter_by(stock_id = stock_id, is_active=1).first()
                print(stock)

                if stock.balance_units < units:
                    return APIResponse().dump(dict(message = 'Not enough stocks to purchase')), 404
                
                stock.balance_units = stock.balance_units - units

                transaction = Transactions(
                    transaction_id =uuid.uuid4(),
                    user_id = session['user_id'],
                    stock_id = stock_id, 
                    transaction_type = 0,
                    units_exercised = units,
                    exercised_price = stock.exercise_price,
                    created_ts = datetime.datetime.utcnow()
                )
                db.session.add(transaction)

                user_stock = UserStocks.query.filter_by(user_id = session['user_id'], stock_id = stock_id).first()
                if not user_stock:
                    user_stock = UserStocks(
                        id = uuid.uuid4(),
                        user_id = session['user_id'],
                        stock_id = stock_id,
                        stock_units = units,
                        is_active = 1,
                        created_ts =  datetime.datetime.utcnow()
                    )
                    db.session.add(user_stock)
                else:
                    user_stock.stock_units = user_stock.stock_units + units
                    
                db.session.commit()

                return APIResponse().dump(dict(message = 'Buy activity is successfully performed')), 200
            else:
                print('not logged in')
                return APIResponse().dump(dict(message= 'User is not logged in')), 401

        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Not able to buy stocks: {str(e)}')), 400
        
api.add_resource(BuyStocksAPI, '/buy')
docs.register(BuyStocksAPI)


class SellStocksAPI(MethodResource, Resource):
    @doc(description = 'Sell Stocks API', tags=['SellStocks API'])
    @use_kwargs(StocksRequest, location = ('json'))
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            if session['user_id']:
                stock_id = kwargs['stock_id']
                units = kwargs['units']
                if units <=0:
                    return APIResponse().dump(dict(message = 'Units must be more than zero')), 400
                
                stock = Stocks.query.filter_by(stock_id = stock_id, is_active=1).first()

                user_stock = UserStocks.query.filter_by(user_id = session['user_id'], stock_id = stock_id).first()

                if not user_stock:
                    return APIResponse().dump(dict(message  = " Stocks not purchased yet")), 400
                else:
                    if user_stock.stock_units < units:
                        return APIResponse().dump(dict(message = 'Not enough stocks to sell')), 400
                    
                    stock.balance_units = stock.balance_units + units
                    user_stock.stock_units = user_stock.stock_units - units

                transaction = Transactions(
                    transaction_id = uuid.uuid4(),
                    user_id = session['user_id'],
                    stock_id = stock_id,
                    transaction_type = 1,
                    units_exercised = units,
                    exercised_price = stock.exercise_price,
                    created_ts = datetime.datetime.utcnow()
                )
                db.session.add(transaction)
                db.session.commit()

                return APIResponse().dump(dict(message = "Sell Activity completed successfully")), 200

            else:
                return APIResponse().dump(dict(message = 'User Not Logged IN')), 401

        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Unable to sell stocks: {str(e)}')), 400
        
api.add_resource(SellStocksAPI, '/sell')
docs.register(SellStocksAPI)


class TransactionsAPI(MethodResource, Resource):
    @doc(decription = 'Transaction API', tags = ['Transaction API'])
    @marshal_with(TransactionResponse)
    def get(self):
        try:
            if session['user_id']:
                trans = Transactions.query.filter_by(user_id = session['user_id'])
                trans_list = list()
                for tran in trans:
                    stock_dict = {}
                    stock_dict['stock_id'] = tran.stock_id
                    stock_dict['stock_name'] =  Stocks.query.filter_by(stock_id = tran.stock_id).first().stock_name
                    stock_dict['units_transacted'] = tran.units_exercised
                    stock_dict['exercised_price'] = tran.exercised_price
                    stock_dict['transaction_type'] = 'Buy' if tran.transaction_type == 0 else 'Sell'
                    stock_dict['transaction_date'] = tran.created_ts

                    trans_list.append(stock_dict)
                print(trans_list)
                return TransactionResponse().dump(dict(transactions = trans_list)), 200
            
            else:
                return APIResponse().dump(dict(message = 'user not logged in')), 401
            
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Unable to list transactions: {str(e)}'))
        

api.add_resource(TransactionsAPI, '/transactions')
docs.register(TransactionsAPI)


class HoldingsAPI(MethodResource, Resource):
    @doc(description='Holdings API', tags = ['Holdings API'])
    @marshal_with(StocksListResponse)
    def get(self):
        try:
            if session['user_id']:
                holdings = UserStocks.query.filter_by(user_id = session['user_id'], is_active=1) 
                holdings_list = list()
                for stock in holdings:
                    stock_dict = {}
                    stock_dict['stock_id'] = stock.stock_id
                    stock_dict['stock_name'] = Stocks.query.filter_by(stock_id = stock.stock_id).first().stock_name
                    stock_dict['stock_units'] = stock.stock_units

                    holdings_list.append(stock_dict)
                print(holdings_list)
                return StocksListResponse().dump(dict(stocks = holdings_list)), 200
            
            else:
                print('user not logged in')
                return APIResponse().dump(dict(message = 'User is not logged in')), 401
            
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Not able to list user stocks: {str(e)}')), 400
        
api.add_resource(HoldingsAPI, '/holdings')
docs.register(HoldingsAPI)


class DeRegisterAPI(MethodResource, Resource):
    @doc(description = 'DeRegister User API', tags = ['DeRegister User API'])
    @marshal_with(APIResponse)
    def delete(self):
        try:
            if session['user_id']:
                user = Users.query.filter_by(user_id = session['user_id']).first()
                user.is_active = 0
                db.session.commit()
                session['user_id'] = None
                print('logged out')
                return APIResponse().dump(dict(message = "User is successfully de registered")), 200
            else:
                return APIResponse().dump(dict(message = 'User is not logged in'))
            
        except Exception as e:
            print(str(e))
            return APIResponse().dump(dict(message = f'Unable to de register user: {str(e)}')), 400

api.add_resource(DeRegisterAPI, '/deregister')
docs.register(DeRegisterAPI) 
            



               
                






