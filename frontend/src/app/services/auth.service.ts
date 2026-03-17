import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {

  private baseUrl = environment.apiUrl;   // http://localhost:8000

  constructor(private http: HttpClient) {}

  login(data:any): Observable<any>{
    return this.http.post(`${this.baseUrl}/api/user/login`, data);
  }

  signup(data:any): Observable<any>{
    return this.http.post(`${this.baseUrl}/api/user/signup`, data);
  }

  saveToken(token:string){
    localStorage.setItem("token",token);
  }

  getToken(){
    return localStorage.getItem("token");
  }

  logout(){
    localStorage.removeItem("token");
  }
}