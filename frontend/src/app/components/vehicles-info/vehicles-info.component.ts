import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { VehicleDetailComponent } from '../vehicle-detail/vehicle-detail.component';


export interface VehicleItem {
  id: string;
  year: number;
  make: string;
  model: string;
  vin: string;
  odometer: number;
  status?: 'ok' | 'warning' | 'critical';
  active_dtcs?: string[];
}

@Component({
  selector: 'app-vehicles-info',
  templateUrl: './vehicles-info.component.html',
  imports: [CommonModule, VehicleDetailComponent],
  styleUrls: ['./vehicles-info.component.scss']
})
export class VehiclesinfoComponent implements OnInit {

  
  @Input() vehicles: VehicleItem[] = [];

  selectedVehicle: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {

    this.vehicles = [
  {
    id: 'VH001',
    year: 2020,
    make: 'Honda',
    model: 'Accord',
    vin: '1HGCM82633A004352',
    odometer: 45320,
    status: 'ok'
  },
  {
    id: 'VH002',
    year: 2021,
    make: 'Toyota',
    model: 'Camry',
    vin: '4T1BF1FK7HU345123',
    odometer: 31200,
    status: 'warning',
    active_dtcs: ['P0133']
  },
  {
    id: '3',
    year: 2019,
    make: 'Tesla',
    model: 'Model 3',
    vin: '5YJ3E1EA7KF317xxx',
    odometer: 58200,
    status: 'critical',
    active_dtcs: ['P0AA1', 'P1B2F']
  }
];
    
  }

  selectVehicle(v: any) {
    this.selectedVehicle = v;
  }
}